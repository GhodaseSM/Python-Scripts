"""Focused regression tests for PDF to Audio's invalid-input path."""

import io
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "PDF to Audio" / "audio_book.py"
PDF_FIXTURE = b"caller-owned PDF fixture bytes"


def invoke_audio_book(start_value, pdf_stream, observed):
    """Execute only audio_book.py while mocking every external interaction."""
    speaker = MagicMock(name="speaker")
    page = MagicMock(name="pdf_page")
    page.extractText.return_value = "mock extracted text"
    reader = MagicMock(name="pdf_reader")
    reader.numPages = 2
    reader.getPage.return_value = page

    pyttsx3_stub = types.ModuleType("pyttsx3")
    pyttsx3_stub.init = Mock(return_value=speaker)
    pypdf2_stub = types.ModuleType("PyPDF2")
    reader_constructor = Mock(return_value=reader)
    pypdf2_stub.PdfFileReader = reader_constructor

    def mocked_open(path, mode):
        observed["open_calls"].append((path, mode))
        return pdf_stream

    observed.update(
        speaker=speaker,
        reader=reader,
        reader_constructor=reader_constructor,
        open_calls=[],
    )
    with (
        patch.dict(sys.modules, {"pyttsx3": pyttsx3_stub, "PyPDF2": pypdf2_stub}),
        patch("builtins.open", side_effect=mocked_open),
        patch("builtins.input", side_effect=lambda _prompt: start_value()),
        patch("sys.stdout", new_callable=io.StringIO),
    ):
        runpy.run_path(str(TARGET), run_name="audio_book_under_test")


class AudioBookFailurePathTests(unittest.TestCase):
    def test_empty_page_input_preserves_state_and_retry_succeeds(self):
        caller_input = {"value": ""}
        caller_pdf = io.BytesIO(PDF_FIXTURE)
        caller_pdf_bytes = caller_pdf.getvalue()
        failed_call = {}

        with self.assertRaises(ValueError):
            invoke_audio_book(lambda: caller_input["value"], caller_pdf, failed_call)

        self.assertEqual(caller_input, {"value": ""})
        self.assertEqual(caller_pdf.getvalue(), caller_pdf_bytes)
        self.assertFalse(caller_pdf.closed)
        self.assertEqual(failed_call["open_calls"], [])
        failed_call["reader_constructor"].assert_not_called()
        failed_call["speaker"].assert_not_called()

        # Retry using the same caller-owned stream after correcting only the input.
        caller_input["value"] = "2"
        successful_call = {}
        invoke_audio_book(lambda: caller_input["value"], caller_pdf, successful_call)

        self.assertEqual(successful_call["open_calls"], [("python_basics.pdf", "rb")])
        successful_call["reader_constructor"].assert_called_once_with(caller_pdf)
        successful_call["reader"].getPage.assert_called_once_with(1)
        successful_call["speaker"].say.assert_called_once_with("mock extracted text")
        successful_call["speaker"].runAndWait.assert_called_once_with()
        self.assertEqual(caller_pdf.getvalue(), caller_pdf_bytes)
        self.assertFalse(caller_pdf.closed)

    def test_valid_input_invokes_only_mocked_pdf_and_speech_apis(self):
        caller_pdf = io.BytesIO(PDF_FIXTURE)
        observed = {}

        invoke_audio_book(lambda: "2", caller_pdf, observed)

        self.assertEqual(observed["open_calls"], [("python_basics.pdf", "rb")])
        observed["reader_constructor"].assert_called_once_with(caller_pdf)
        observed["reader"].getPage.assert_called_once_with(1)
        observed["speaker"].say.assert_called_once_with("mock extracted text")
        observed["speaker"].runAndWait.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
