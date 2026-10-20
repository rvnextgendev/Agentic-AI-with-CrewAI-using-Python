import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI
from openai import APIError

from config.llm import GroqReActChatModel


class GroqStreamTests(unittest.TestCase):
    def setUp(self):
        self.model = GroqReActChatModel(api_key="test", model="qwen/qwen3.8-27b")

    def test_partial_rate_limited_attempt_is_discarded(self):
        attempts = []

        def stream(*args, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                yield ChatGenerationChunk(message=AIMessageChunk(content="partial action"))
                raise APIError("Rate limit reached", Mock(), body=None)
            yield ChatGenerationChunk(message=AIMessageChunk(content="Final Answer: OK"))

        callback = Mock()
        with patch.object(ChatOpenAI, "_stream", stream), patch("config.llm.time.sleep") as sleep:
            chunks = list(self.model._stream([], run_manager=callback))
        self.assertEqual([c.text for c in chunks], ["Final Answer: OK"])
        self.assertEqual(callback.on_llm_new_token.call_count, 1)
        sleep.assert_called_once_with(65)

    def test_other_api_errors_are_not_retried(self):
        with patch.object(ChatOpenAI, "_stream", side_effect=APIError("Invalid request", Mock(), body=None)), patch("config.llm.time.sleep") as sleep:
            with self.assertRaises(APIError):
                list(self.model._stream([]))
        sleep.assert_not_called()

    def test_rate_limit_retries_are_bounded(self):
        with patch.object(ChatOpenAI, "_stream", side_effect=APIError("Rate limit reached", Mock(), body=None)) as stream, patch("config.llm.time.sleep") as sleep:
            with self.assertRaises(APIError):
                list(self.model._stream([]))
        self.assertEqual(stream.call_count, 4)
        self.assertEqual(sleep.call_count, 3)

    def test_parse_failure_discards_partial_output_and_retries_with_instruction(self):
        original = []
        attempts = []

        def stream(model, messages, **kwargs):
            attempts.append(list(messages))
            if len(attempts) == 1:
                yield ChatGenerationChunk(message=AIMessageChunk(content="bad partial action"))
                raise APIError("Parsing failed", Mock(), body={"error": {"code": "output_parse_failed", "failed_generation": "unsafe raw output"}})
            yield ChatGenerationChunk(message=AIMessageChunk(content="Final Answer: OK"))

        with patch.object(ChatOpenAI, "_stream", stream):
            chunks = list(self.model._stream(original))
        self.assertEqual([c.text for c in chunks], ["Final Answer: OK"])
        self.assertEqual(original, [])
        self.assertIn("plain text", attempts[1][-1].content)
        self.assertNotIn("unsafe raw output", attempts[1][-1].content)

    def test_parse_retry_is_bounded(self):
        error = APIError("Parsing failed", Mock(), body={"code": "output_parse_failed"})
        with patch.object(ChatOpenAI, "_stream", side_effect=error) as stream:
            with self.assertRaises(APIError):
                list(self.model._stream([]))
        self.assertEqual(stream.call_count, 2)

    def test_non_streaming_parse_error_is_also_retried(self):
        error = APIError("Parsing failed", Mock(), body={"code": "output_parse_failed"})
        with patch.object(ChatOpenAI, "_generate", side_effect=[error, "success"]) as generate:
            result = self.model._generate([])
        self.assertEqual(result, "success")
        self.assertEqual(generate.call_count, 2)


if __name__ == "__main__":
    unittest.main()
