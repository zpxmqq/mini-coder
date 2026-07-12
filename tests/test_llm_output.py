import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_parse_llm_json_object_accepts_markdown_and_explanation():
    from infra.llm_output import parse_llm_json_object

    raw = '''
    解析结果如下：
    ```json
    {"action": "skip", "reason": "内容重复"}
    ```
    请按照结果继续处理。
    '''

    assert parse_llm_json_object(raw) == {
        "action": "skip",
        "reason": "内容重复",
    }


def test_parse_llm_json_array_accepts_markdown_fence():
    from infra.llm_output import parse_llm_json_array

    raw = '''
    ```json
    [
      {"memory_type": "fact", "content": "用户正在开发 mini-coder"}
    ]
    ```
    '''

    assert parse_llm_json_array(raw) == [
        {"memory_type": "fact", "content": "用户正在开发 mini-coder"}
    ]


def test_llm_json_parser_rejects_wrong_root_type():
    from infra.llm_output import parse_llm_json_array, parse_llm_json_object

    assert parse_llm_json_object('[{"value": 1}]') is None
    assert parse_llm_json_array('{"value": 1}') is None


def test_llm_json_parser_rejects_invalid_or_empty_text():
    from infra.llm_output import parse_llm_json_array, parse_llm_json_object

    assert parse_llm_json_object("这不是 JSON") is None
    assert parse_llm_json_array("") is None


if __name__ == "__main__":
    test_parse_llm_json_object_accepts_markdown_and_explanation()
    test_parse_llm_json_array_accepts_markdown_fence()
    test_llm_json_parser_rejects_wrong_root_type()
    test_llm_json_parser_rejects_invalid_or_empty_text()
    print("LLM output parser tests passed")
