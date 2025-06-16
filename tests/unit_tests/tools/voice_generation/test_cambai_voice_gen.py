import pytest
from unittest.mock import patch, Mock
from superagi.tools.voice_generation.cambai_voice_gen import CambAIVoiceGenTool


@pytest.fixture
def cambai_tool():
    """Create a CambAI tool instance with mocked dependencies."""
    tool = CambAIVoiceGenTool()
    tool.resource_manager = Mock()
    
    # Mock toolkit_config
    tool.toolkit_config = Mock()
    tool.toolkit_config.toolkit_id = 1
    tool.toolkit_config.get_tool_config = Mock(return_value="fake_api_key")
    
    # Mock session and toolkit query
    mock_session = Mock()
    mock_toolkit = Mock()
    mock_toolkit.organisation_id = "test_org_id"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_toolkit
    tool.toolkit_config.session = mock_session
    
    return tool


def test_init():
    """Test tool initialization."""
    tool = CambAIVoiceGenTool()
    assert tool.name == "CambAIVoiceGenTool"
    assert tool.description is not None
    assert hasattr(tool, 'args_schema')


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
@patch('superagi.tools.voice_generation.cambai_voice_gen.time')
def test_execute_success(mock_time, mock_requests, cambai_tool):
    """Test successful voice generation."""
    tool = cambai_tool
    
    # Mock time.time() for timeout handling
    mock_time.time.side_effect = [0, 1, 2]  # start, first check, second check
    mock_time.sleep = Mock()
    
    # Mock the three API calls
    # 1. Create TTS task
    mock_create_response = Mock()
    mock_create_response.status_code = 200
    mock_create_response.json.return_value = {"task_id": "test_task_id"}
    
    # 2. Poll task status
    mock_status_response = Mock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {"status": "SUCCESS", "run_id": "test_run_id"}
    
    # 3. Get audio result
    mock_audio_response = Mock()
    mock_audio_response.status_code = 200
    mock_audio_response.content = b"fake_audio_data"
    
    mock_requests.post.return_value = mock_create_response
    mock_requests.get.side_effect = [mock_status_response, mock_audio_response]
    
    # Mock resource manager
    tool.resource_manager.write_binary_file.return_value = "File written successfully"
    
    # Execute
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    # Assertions
    assert "Audio file generated successfully" in result
    assert "test_output.wav" in result
    
    # Verify API calls
    mock_requests.post.assert_called_once_with(
        "https://client.camb.ai/apis/tts",
        headers={"x-api-key": "fake_api_key", "Content-Type": "application/json"},
        json={"text": "Hello world", "voice_id": 20303, "language": 1}
    )
    
    # Verify status check
    mock_requests.get.assert_any_call(
        "https://client.camb.ai/apis/tts/test_task_id",
        headers={"x-api-key": "fake_api_key"}
    )
    
    # Verify audio download
    mock_requests.get.assert_any_call(
        "https://client.camb.ai/apis/tts-result/test_run_id",
        headers={"x-api-key": "fake_api_key"},
        timeout=30
    )
    
    # Verify file write
    tool.resource_manager.write_binary_file.assert_called_once_with("test_output.wav", b"fake_audio_data")


def test_execute_missing_api_key():
    """Test error handling when API key is missing."""
    tool = CambAIVoiceGenTool()
    tool.resource_manager = Mock()
    
    # Mock toolkit_config to return None for API key
    tool.toolkit_config = Mock()
    tool.toolkit_config.get_tool_config = Mock(return_value=None)
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: Missing CambAI API key" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
def test_execute_create_task_failure(mock_requests, cambai_tool):
    """Test error handling when TTS task creation fails."""
    tool = cambai_tool
    
    # Mock failed create task response
    mock_create_response = Mock()
    mock_create_response.status_code = 400
    mock_create_response.text = "Bad request"
    mock_requests.post.return_value = mock_create_response
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: Failed to create TTS task" in result
    assert "Status code: 400" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
def test_execute_no_task_id(mock_requests, cambai_tool):
    """Test error handling when no task_id is returned."""
    tool = cambai_tool
    
    # Mock create response without task_id
    mock_create_response = Mock()
    mock_create_response.status_code = 200
    mock_create_response.json.return_value = {}
    mock_requests.post.return_value = mock_create_response
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: No task_id returned from Camb AI API" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
@patch('superagi.tools.voice_generation.cambai_voice_gen.time')
def test_execute_task_failed(mock_time, mock_requests, cambai_tool):
    """Test error handling when TTS task fails."""
    tool = cambai_tool
    
    mock_time.time.side_effect = [0, 1]
    mock_time.sleep = Mock()
    
    # Mock successful create task
    mock_create_response = Mock()
    mock_create_response.status_code = 200
    mock_create_response.json.return_value = {"task_id": "test_task_id"}
    
    # Mock failed status response
    mock_status_response = Mock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {"status": "FAILED", "error": "Task processing failed"}
    
    mock_requests.post.return_value = mock_create_response
    mock_requests.get.return_value = mock_status_response
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: TTS task failed" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
@patch('superagi.tools.voice_generation.cambai_voice_gen.time')
def test_execute_timeout(mock_time, mock_requests, cambai_tool):
    """Test timeout handling during task polling."""
    tool = cambai_tool
    
    # Mock time to simulate timeout
    mock_time.time.side_effect = [0, 70]  # start at 0, check at 70 seconds (timeout is 60)
    mock_time.sleep = Mock()
    
    # Mock successful create task
    mock_create_response = Mock()
    mock_create_response.status_code = 200
    mock_create_response.json.return_value = {"task_id": "test_task_id"}
    mock_requests.post.return_value = mock_create_response
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: Timed out waiting for TTS task to complete" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
@patch('superagi.tools.voice_generation.cambai_voice_gen.time')
def test_execute_audio_download_failure(mock_time, mock_requests, cambai_tool):
    """Test error handling when audio download fails."""
    tool = cambai_tool
    
    mock_time.time.side_effect = [0, 1]
    mock_time.sleep = Mock()
    
    # Mock successful create task and status check
    mock_create_response = Mock()
    mock_create_response.status_code = 200
    mock_create_response.json.return_value = {"task_id": "test_task_id"}
    
    mock_status_response = Mock()
    mock_status_response.status_code = 200
    mock_status_response.json.return_value = {"status": "SUCCESS", "run_id": "test_run_id"}
    
    # Mock failed audio download
    mock_audio_response = Mock()
    mock_audio_response.status_code = 404
    mock_audio_response.text = "Not found"
    
    mock_requests.post.return_value = mock_create_response
    mock_requests.get.side_effect = [mock_status_response, mock_audio_response]
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: Failed to get audio result" in result
    assert "Status code: 404" in result
    tool.resource_manager.write_binary_file.assert_not_called()


@patch('superagi.tools.voice_generation.cambai_voice_gen.requests')
def test_execute_requests_exception(mock_requests, cambai_tool):
    """Test error handling when requests raises an exception."""
    tool = cambai_tool
    
    # Mock requests to raise an exception
    mock_requests.post.side_effect = Exception("Network error")
    
    result = tool._execute("Hello world", 20303, 1, "test_output.wav")
    
    assert "Error: Network error" in result
    tool.resource_manager.write_binary_file.assert_not_called()


def test_execute_wav_extension_added(cambai_tool):
    """Test that .wav extension is added if not present."""
    tool = cambai_tool
    
    with patch('superagi.tools.voice_generation.cambai_voice_gen.requests') as mock_requests, \
         patch('superagi.tools.voice_generation.cambai_voice_gen.time') as mock_time:
        
        mock_time.time.side_effect = [0, 1]
        mock_time.sleep = Mock()
        
        # Mock successful API responses
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {"task_id": "test_task_id"}
        
        mock_status_response = Mock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = {"status": "SUCCESS", "run_id": "test_run_id"}
        
        mock_audio_response = Mock()
        mock_audio_response.status_code = 200
        mock_audio_response.content = b"fake_audio_data"
        
        mock_requests.post.return_value = mock_create_response
        mock_requests.get.side_effect = [mock_status_response, mock_audio_response]
        
        tool.resource_manager.write_binary_file.return_value = "File written successfully"
        
        # Execute with filename without .wav extension
        result = tool._execute("Hello world", 20303, 1, "test_output")
        
        # Verify .wav extension was added
        tool.resource_manager.write_binary_file.assert_called_once_with("test_output.wav", b"fake_audio_data")
        assert "test_output.wav" in result