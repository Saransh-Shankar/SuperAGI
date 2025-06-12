import os
import tempfile
from unittest.mock import patch, Mock, MagicMock

import pytest

from superagi.tools.voice_generation.cambai_voice_gen import CambAIVoiceGenTool


class MockToolkitConfig:
    def get_tool_config(self, key):
        configs = {
            'CAMB_API_KEY': 'fake_api_key',
        }
        return configs.get(key)


class MockCambAI:
    def __init__(self, api_key):
        self.api_key = api_key

    def text_to_speech(self, text, voice_id, save_to_file):
        # Create a dummy audio file
        with open(save_to_file, 'wb') as f:
            f.write(b'dummy audio data')


@pytest.fixture
def cambai_voice_gen_tool():
    with patch('superagi.tools.voice_generation.cambai_voice_gen.CambAI', MockCambAI):
        tool = CambAIVoiceGenTool()
        tool.resource_manager = Mock()
        # Set the toolkit_config instead of directly setting get_tool_config
        tool.toolkit_config = MockToolkitConfig()
        yield tool


def test_init():
    tool = CambAIVoiceGenTool()
    assert tool.name == "CambAIVoiceGenTool"
    assert tool.description is not None
    assert hasattr(tool, 'args_schema')


def test_execute(cambai_voice_gen_tool):
    # Setup
    tool = cambai_voice_gen_tool
    tool.resource_manager.write_binary_file.return_value = "File write successful"
    
    # Create a temp file for testing
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Test execution
        text = "This is a test text for voice generation"
        voice_id = 20303
        output_file_path = "test_output.wav"
        
        result = tool._execute(text, voice_id, output_file_path)
        
        # Assertions
        assert "Audio file generated successfully" in result
        assert output_file_path in result
        tool.resource_manager.write_binary_file.assert_called_once()
        
        # Test with missing API key
        # Create a new mock toolkit config that returns None
        class MockToolkitConfigNone:
            def get_tool_config(self, key):
                return None
        
        # Replace the toolkit_config
        tool.toolkit_config = MockToolkitConfigNone()
        result = tool._execute(text, voice_id, output_file_path)
        assert "Error: Missing CambAI API key" in result
    
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_execute_with_exception(cambai_voice_gen_tool):
    # Setup
    tool = cambai_voice_gen_tool
    
    # Mock CambAI to raise an exception
    with patch('superagi.tools.voice_generation.cambai_voice_gen.CambAI.text_to_speech', 
               side_effect=Exception("Test exception")):
        
        # Test execution
        result = tool._execute("Test text", 20303, "test_output.wav")
        
        # Assertions
        assert "Error: Test exception" in result