import copy
import unittest.mock
from unittest.mock import patch
from marqo.errors import IndexNotFoundError, InvalidArgError
from marqo.tensor_search import tensor_search
from marqo.tensor_search.enums import TensorField, IndexSettingsField, SearchMethod
from tests.marqo_test import MarqoTestCase
from marqo.tensor_search.models.api_models import BulkSearchQuery, BulkSearchQueryEntity
from pprint import pprint
from marqo.tensor_search.tensor_search import _create_normal_tensor_search_query
from pydantic.error_wrappers import ValidationError

class TestScoreModifiersSearch(MarqoTestCase):

    def setUp(self):
        self.index_name = "test-index"

        try:
            tensor_search.delete_index(config=self.config, index_name=self.index_name)
        except:
            pass

        tensor_search.create_vector_index(
            index_name=self.index_name, config=self.config, index_settings={
                IndexSettingsField.index_defaults: {
                    IndexSettingsField.model: "ViT-B/32",
                    IndexSettingsField.treat_urls_and_pointers_as_images: True,
                    IndexSettingsField.normalize_embeddings: True
                }
            })
        pass

        self.test_valid_score_modifiers_list = [
            {
                # miss one weight
                "multiply_score_by":
                    [{"field_name": "multiply_1",
                      "weight": 1,},
                     {"field_name": "multiply_2",}],
                "add_to_score": [
                    {"field_name": "add_1", "weight" : -3,
                     },
                    {"field_name": "add_2", "weight": 1,
                     }]
            },
            {
                # 0 weight
                "multiply_score_by":
                    [{"field_name": "multiply_1",
                      "weight": 1.0, },
                     {"field_name": "multiply_2",
                      "weight": 0}],
                "add_to_score": [
                    {"field_name": "add_1", "weight": -3,
                     },
                    {"field_name": "add_2", "weight": 1,
                     }]
            },
            {
                # remove one field
                "multiply_score_by":
                    [
                     {"field_name": "multiply_2",
                      "weight": 1.2}],
                "add_to_score": [
                    {"field_name": "add_1", "weight": -3,
                     },
                    {"field_name": "add_2", "weight": 1,
                     }]
            },
            {
                # missing "multipy_score_by"
                "add_to_score": [
                    {"field_name": "add_1", "weight": -3,
                     },
                    {"field_name": "add_2", "weight": 1,
                     }]
            },
            {
                # missing "add_to_score"
                "multiply_score_by":
                    [{"field_name": "multiply_2",
                      "weight": 1.2}],
            },
        ]

        self.test_score_documents = [
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # 4 fields
             "multiply_1": 1,
             "multiply_2": 20.0,
             "add_1": 1.0,
             "add_2": 30.0,
             "_id": "1"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # let's multiply by 0
             "multiply_1": 0,
             "multiply_2": 20.0,
             "add_1": 1.0,
             "add_2": 3.0,
             "_id": "2"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # 2 fields
             "multiply_2": 20.3,
             "add_1": 1.2,
             "_id": "3"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # change order
             "add_1": 1.0,
             "add_2": 3.0,
             "multiply_1": 1,
             "multiply_2": -20.0,
             "_id": "4"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # float
             "multiply_1": 1,
             "multiply_2": 2.531,
             "add_1": 1.454,
             "add_2": -3.692,
             "_id": "5"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             "_id": "0",
             "filter": "original"
             },
        ]

    def tearDown(self) -> None:
        try:
            tensor_search.delete_index(config=self.config, index_name=self.index_name)
        except:
            pass

    def test_search_result_not_affected_if_fields_not_exist(self):
        documents = [
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             "_id": "0",
             "filter": "original"
             },
        ]

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)


        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                             text = "what is the rider doing?", score_modifiers=None, result_count=10)

        normal_score = normal_res["hits"][0]["_score"]

        modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                text = "what is the rider doing?",
                                                score_modifiers={
                                                    "multiply_score_by":
                                                        [{"field_name": "multiply_1",
                                                          "weight": 1,},
                                                         {"field_name": "multiply_2",}
                                                        ],
                                                    "add_to_score": [
                                                        {"field_name": "add_1",
                                                         },
                                                        {"field_name": "add_2",
                                                         }
                                                    ]
                                                })

        modifier_score = modifier_res["hits"][0]["_score"]
        self.assertEqual(normal_score, modifier_score)

    def get_expected_score(self, doc, ori_score, score_modifiers):
        add = 0.0
        for config in score_modifiers.get("multiply_score_by", []):
            field_name = config["field_name"]
            weight = config.get("weight", 1)
            if field_name in doc:
                if isinstance(doc[field_name], (int, float)):
                    ori_score = ori_score * weight * doc[field_name]

        for config in score_modifiers.get("add_to_score", []):
            field_name = config["field_name"]
            weight = config.get("weight", 1)
            if field_name in doc:
                if isinstance(doc[field_name], (int, float)):
                    add = add + weight * doc[field_name]
        return max(0.0, (ori_score + add))

    def test_search_score_modified_as_expected(self):
        documents = self.test_score_documents

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                          text="what is the rider doing?", score_modifiers=None, result_count=10)
        normal_score = normal_res["hits"][0]["_score"]


        epsilon = 1e-5
        score_modifiers_list = self.test_valid_score_modifiers_list
        for score_modifiers in score_modifiers_list:
            modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                    text = "what is the rider doing?",
                                                    score_modifiers=score_modifiers, result_count=10)

            assert len(modifier_res["hits"]) == len(documents)
            for result in modifier_res["hits"]:
                expected_score = self.get_expected_score(result, normal_score, score_modifiers)
                if abs(expected_score - result["_score"]) > epsilon:
                    raise AssertionError

    def test_search_score_modified_as_expected_with_filter(self):
        documents = self.test_score_documents

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                          text="what is the rider doing?", score_modifiers=None, result_count=10)
        normal_score = normal_res["hits"][0]["_score"]

        epsilon = 1e-5
        score_modifiers_list = self.test_valid_score_modifiers_list
        for score_modifiers in score_modifiers_list:
            modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                text="what is the rider doing?",
                                                score_modifiers=score_modifiers, result_count=10,
                                                filter="filter:original")

            assert len(modifier_res["hits"]) == 1
            assert modifier_res["hits"][0]["_id"] == "0"
            for result in modifier_res["hits"]:
                expected_score = self.get_expected_score(result, normal_score, score_modifiers)
                if abs(expected_score - result["_score"]) > epsilon:
                    raise AssertionError

    def test_search_score_modified_as_expected_with_searchable_attributes(self):
        documents = self.test_score_documents

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                          text="what is the rider doing?", score_modifiers=None, result_count=10,
                                          searchable_attributes=["my_image_field"])
        normal_score = normal_res["hits"][0]["_score"]

        epsilon = 1e-5
        score_modifiers_list = self.test_valid_score_modifiers_list
        for score_modifiers in score_modifiers_list:
            modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                text="what is the rider doing?",
                                                score_modifiers=score_modifiers, result_count=10,
                                                searchable_attributes=["my_image_field"])

            assert len(modifier_res["hits"]) == len(documents)
            for result in modifier_res["hits"]:
                expected_score = self.get_expected_score(result, normal_score, score_modifiers)
                if abs(expected_score - result["_score"]) > epsilon:
                    raise AssertionError

    def test_search_score_modified_as_expected_with_attributes_to_retrieve(self):
        documents = self.test_score_documents
        invalid_fields = copy.deepcopy(documents[0])
        del invalid_fields["_id"]

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                          text="what is the rider doing?", score_modifiers=None, result_count=10,)
        normal_score = normal_res["hits"][0]["_score"]

        epsilon = 1e-5
        score_modifiers_list = self.test_valid_score_modifiers_list
        for score_modifiers in score_modifiers_list:
            modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                text="what is the rider doing?",
                                                score_modifiers=score_modifiers, result_count=10,
                                                attributes_to_retrieve=["_id"])

            assert len(modifier_res["hits"]) == len(documents)
            for result in modifier_res["hits"]:
                for field in list(invalid_fields):
                    assert field not in result
                # need to get the original doc with score modifier fields to compute expected score
                original_doc = [doc for doc in documents if doc["_id"] == result["_id"]][0]
                expected_score = self.get_expected_score(original_doc, normal_score, score_modifiers)
                if abs(expected_score - result["_score"]) > epsilon:
                    raise AssertionError

    def test_search_score_modified_as_expected_with_skipped_fields(self):
        # multiply_1 is string here, which should be skipped in modification
        documents = [
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # 4 fields
             "multiply_1": "1",
             "multiply_2": 20.0,
             "add_1": 1.0,
             "add_2": 30.0,
             "_id": "1"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # let's multiply by 0
             "multiply_1": "0",
             "multiply_2": 20.0,
             "add_1": 1.0,
             "add_2": 3.0,
             "_id": "2"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # 2 fields
             "multiply_2": 20.3,
             "add_1": 1.2,
             "_id": "3"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # change order
             "add_1": 1.0,
             "add_2": 3.0,
             "multiply_1": "1",
             "multiply_2": -20.0,
             "_id": "4"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # float
             "multiply_1": "1",
             "multiply_2": 2.531,
             "add_1": 1.454,
             "add_2": -3.692,
             "_id": "5"
             },
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             "_id": "0",
             "filter": "original"
             },
        ]

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)

        normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                          text="what is the rider doing?", score_modifiers=None, result_count=10)
        normal_score = normal_res["hits"][0]["_score"]

        epsilon = 1e-5
        score_modifiers_list = self.test_valid_score_modifiers_list
        for score_modifiers in score_modifiers_list:
            modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                    text = "what is the rider doing?",
                                                    score_modifiers=score_modifiers, result_count=10)

            assert len(modifier_res["hits"]) == len(documents)
            for result in modifier_res["hits"]:
                expected_score = self.get_expected_score(result, normal_score, score_modifiers)
                if abs(expected_score - result["_score"]) > epsilon:
                    raise AssertionError

    def test_expected_error_raised(self):
        documents = [
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             # 4 fields
             "multiply_1": 1,
             "multiply_2": 20.0,
             "add_1": 1.0,
             "add_2": 30.0,
             "_id": "1"
             },
        ]

        invalid_score_modifiers_list = [
            {
                # typo in multiply_score_by
                "multiply_scores_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in add_to_score
                "multiply_score_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_ssto_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in field_name
                "multiply_score_by":
                    [{"field_names": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in weight
                "multiply_score_by":
                    [{"field_names": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # no field name
                "multiply_scores_by":
                    [{"field_names": "reputation",
                      "weights": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_ssto_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # list in field_name value
                "multiply_score_by":
                    [{"field_name": ["repuation", "reputation-test"],
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     },],
                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {
                # field name can't be "_id"
                "multiply_score_by":
                    [{"field_name": "_id",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {
                # weight to be str
                "multiply_score_by":
                    [{"field_name": "reputation",
                      "weight": "1",
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            { # empty
            },
            {
                # one part to be None
                "multiply_score_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": None
            },
            {  # one part to be empty
                "multiply_score_by": [],
                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {  # two parts to be empty
                "multiply_score_by": [],
                "add_to_score": [],
            },
        ]

        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        for invalid_score_modifiers in invalid_score_modifiers_list:
            try:
                modifier_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                                    text = "what is the rider doing?",
                                                    score_modifiers=invalid_score_modifiers, result_count=10)
                raise AssertionError
            except InvalidArgError:
                pass

    def test_normal_query_body_is_called(self):
        documents = [
            {"my_text_field": "A rider is riding a horse jumping over the barrier.",
             "my_image_field": "https://raw.githubusercontent.com/marqo-ai/marqo/mainline/examples/ImageSearchGuide/data/image2.jpg",
             "_id": "0",
             "filter": "original"
             },
        ]
        tensor_search.add_documents(config=self.config, index_name=self.index_name, docs=documents,
                                    non_tensor_fields=["multiply_1", "multiply_2", "add_1", "add_2",
                                                       "filter"], auto_refresh=True)
        def pass_create_normal_tensor_search_query(*arg, **kwargs):
            return _create_normal_tensor_search_query(*arg, **kwargs)

        mock_create_normal_tensor_search_query = unittest.mock.MagicMock()
        mock_create_normal_tensor_search_query.side_effect = pass_create_normal_tensor_search_query

        @unittest.mock.patch("marqo.tensor_search.tensor_search._create_normal_tensor_search_query", mock_create_normal_tensor_search_query)
        def run():
            normal_res = tensor_search.search(config=self.config, index_name=self.index_name,
                                              text="what is the rider doing?", score_modifiers=None, result_count=10)
            mock_create_normal_tensor_search_query.assert_called()

            return True
        assert run()

    def test_bulk_search_not_support_score_modifiers(self):
        index_name = "bulk_test"
        score_modifiers = {
                # miss one weight
                "multiply_score_by":
                    [{"field_name": "multiply_1",
                      "weight": 1, },
                     {"field_name": "multiply_2", }],
                "add_to_score": [
                    {"field_name": "add_1", "weight": -3,
                     },
                    {"field_name": "add_2", "weight": 1,
                     }]
            }
        tensor_search.add_documents(
            config=self.config, index_name=index_name, docs=[
                {"abc": "Exact match hehehe", "other field": "baaadd", "_id": "id1-first"},
                {"abc": "random text", "other field": "Close match hehehe", "_id": "id1-second"},
            ], auto_refresh=True
        )
        try:
            response = tensor_search.bulk_search(marqo_config=self.config, query=BulkSearchQuery(
                queries=[
                    BulkSearchQueryEntity(index=index_name, q="hehehe", limit=2, scoreModifiers = score_modifiers),
                ]
            ))
            raise AssertionError
        except (ValidationError, InvalidArgError):
            pass


