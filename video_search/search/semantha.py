import ast
import io
import logging
from abc import abstractmethod
from itertools import filterfalse
from time import perf_counter

import pandas as pd
import semantha_sdk
import streamlit as st
from semantha_sdk.model.document import Document


def _to_text_file(text: str):
    input_file = io.BytesIO(text.encode("utf-8"))
    input_file.name = "input.txt"
    return input_file


class RankingStrategy:

    def __init__(self, semantha):
        self._semantha = semantha

    @abstractmethod
    def rank(self, sentence_references, video_references=None, alpha=0.7) -> list:
        raise NotImplementedError("Abstract method")


class DenseOnlyRanking(RankingStrategy):

    def rank(self, sentence_references, video_references=None, alpha=0.7, sparse_filter_size=5) -> list:
        return sentence_references


class SparseFilterDenseRanking(RankingStrategy):

    def rank(self, sentence_references, video_references=None, alpha=0.7, sparse_filter_size=5) -> list:
        if video_references is None or sentence_references is None or len(sentence_references) == 0:
            return sentence_references
        else:
            video_ids = [self._semantha.parse("id", c) for c in video_references]
            sentence_references[:] = filterfalse(
                lambda sentence: self._semantha.parse("id", sentence) not in video_ids,
                sentence_references
            )
            return sentence_references


class HybridRanking(RankingStrategy):

    def rank(self, sentence_references, video_references=None, alpha=0.7, sparse_filter_size=5) -> list:
        if video_references is None or sentence_references is None or len(sentence_references):
            return sentence_references
        else:
            scored = []
            video_ids = [self._semantha.parse("id", c) for c in video_references]
            for i, sr in enumerate(sentence_references):
                self._semantha.parse("id", sr)
                sentence_id = self._semantha.parse("id", sr)
                video_rank = video_ids.index(sentence_id) if sentence_id in video_ids else None
                score = (1/(i + 1)) + (0 if video_rank is None else (alpha * 1/(video_rank + 1)))
                scored.append((score, sr))
            scored.sort(key=lambda a: a[0], reverse=True)
            return [x for _, x in scored]


class Semantha:
    def __init__(self, demo_config):
        semantha_secrets = st.secrets["semantha"]
        self.__sdk = semantha_sdk.login(
            server_url=semantha_secrets["base_url"],
            key=semantha_secrets["api_key"],
        )
        self.__domain = semantha_secrets["domain"]
        self.__tracking_domain = semantha_secrets.get("tracking_domain", default=None)

    def query_library(self,
                      text: str,
                      tags: str,
                      threshold: float = 0.7,
                      max_matches: int = 3,
                      # ranking_strategy: RankingStrategy.__class__ = DenseOnlyRanking,
                      ranking_strategy: RankingStrategy.__class__ = HybridRanking,
                      sparse_filter_size: int = 5,
                      alpha=0.7,
                      filter_duplicates=False):
        logging.info(f"Search query: '{text}'")
        search_start = perf_counter()
        ranking_start = None
        ranking_end = None
        if st.session_state.control:
            sentence_references = self.__get_sentence_refs_control(text, tags, threshold, max_matches)
        else:
            sentence_references = self.__get_sentence_refs_aiedn(text, tags, threshold, max_matches)

            video_references = None
            if ranking_strategy is SparseFilterDenseRanking or ranking_strategy is HybridRanking:
                video_references = self.__get_video_refs_aiedn(text, tags, sparse_filter_size)

            ranker = ranking_strategy(self)
            ranking_start = perf_counter()
            sentence_references = ranker.rank(sentence_references, video_references, alpha, sparse_filter_size)
            ranking_end = perf_counter()

        result_dict = {}
        if sentence_references is None:
            logging.info(f"No matches found!")
        else:
            logging.info(f"Found {len(sentence_references)} matches.")
            filtered_lib = self.__sdk.domains(self.__domain).reference_documents \
                .get(offset=0,
                     limit=len(sentence_references),
                     filter_document_ids=",".join([str(sr.document_id) for sr in sentence_references]),
                     return_fields="id,contentpreview,tags,metadata,name")
            if filtered_lib is not None and len(filtered_lib.documents) > 0:
                for idx, __ref_doc in enumerate(filtered_lib.documents):
                    result_dict[__ref_doc.id] = {
                        "doc_name": __ref_doc.name,
                        "content": __ref_doc.content_preview,
                        "similarity": sentence_references[idx].similarity,
                        "metadata": __ref_doc.metadata,
                        "tags": set(__ref_doc.tags) - {"TRANSCRIPT", "SEGMENT", "CONTROL"},
                    }
        if filter_duplicates:
            result_dict = self.__filter_duplicates(result_dict)
        search_end = perf_counter()
        logging.info(f"Search took {search_end - search_start} seconds.")
        if ranking_start is not None and ranking_end is not None:
            logging.info(f"Ranking using {ranking_strategy.__name__} strategy took {ranking_end - ranking_start} seconds.")

        return self.__get_matches(result_dict)

    def __get_sentence_refs_control(self, text: str, tags: str, threshold: float, max_matches: int):
        return self.__sdk.domains(self.__domain).references.post(
                file=_to_text_file(text),
                similarity_threshold=threshold,
                max_references=max_matches,
                with_context=False,
                tags="+".join(["CONTROL"] + [tags]),
                mode="document"
            ).references

    def __get_sentence_refs_aiedn(self, text: str, tags: str, threshold: float, max_matches: int):
        return self.__sdk.domains(self.__domain).references.post(
                file=_to_text_file(text),
                similarity_threshold=threshold,
                max_references=max_matches,
                with_context=False,
                tags="SEGMENT+IBM Engineering Lifecycle Management",  # "+".join(["SENTENCE_LEVEL"] + [tags]),
                mode="fingerprint"
            ).references

    def __get_video_refs_aiedn(self, text: str, tags: str, sparse_filter_size: int):
        return self.__sdk.domains(self.__domain).references.post(
                    file=_to_text_file(text),
                    max_references=sparse_filter_size,
                    with_context=False,
                    tags="TRANSCRIPT+IBM Engineering Lifecycle Management",  # "+".join(["TRANSCRIPT_LEVEL"] + [tags]),
                    mode="document"
                ).references

    def add_to_library(self, content: str, tag: str) -> None:
        if not self.__tracking_domain:
            return
        self.__sdk.domains(self.__tracking_domain).reference_documents.post(file=_to_text_file(content), tags=tag)

    @staticmethod
    def __get_matches(results):
        matches = pd.DataFrame.from_records(
            [
                [
                    r["doc_name"],
                    r["content"].replace("\n", " "),
                    int(round(r["similarity"], 2) * 100),
                    r["metadata"],
                    r["tags"],
                ]
                for r in list(results.values())
            ],
            columns=["Name", "Content", "Similarity", "Metadata", "Tags"],
        )
        matches.index = range(1, matches.shape[0] + 1)
        matches.index.name = "Rank"
        return matches

    def __get_document_content(self, doc: Document) -> str:
        content = ""
        for p in doc.pages:
            for c in p.contents:
                content += "\n".join([par.text for par in c.paragraphs])
        return content

    def __get_ref_doc(self, doc_id: str, domain: str) -> Document:
        return self.__sdk.domains(domain).reference_documents(doc_id).get()

    def parse(self, key, document):
        from urllib.parse import urlparse, parse_qs
        document = self.__get_ref_doc(document.document_id, self.__domain)
        value = ast.literal_eval(document.metadata)[key]
        if key == "id":
            # parse id from youtube url
            parse_result = urlparse(value)
            query_params = parse_qs(parse_result.query)
            return query_params["v"][0]

    def __filter_duplicates(self, result_dict):
        __seen_video_ids = []
        __filtered_sentence_references = {}
        for e in result_dict:
            entry = ast.literal_eval(result_dict[e]["metadata"])
            if entry["url"] not in __seen_video_ids:
                __seen_video_ids.append(entry["url"])
                __filtered_sentence_references[e] = result_dict[e]
            else:
                logging.info(f"Found duplicate: {entry['id']}. Removing...")
        logging.info(f"After duplicate filtering {len(__filtered_sentence_references)} matches remain.")
        return __filtered_sentence_references
