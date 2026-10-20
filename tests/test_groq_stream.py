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


if __name__ == "__main__":
    unittest.main()
