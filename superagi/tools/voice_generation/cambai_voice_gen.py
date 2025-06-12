from typing import Type, Optional
import requests
import time

from pydantic import BaseModel, Field
from superagi.resource_manager.file_manager import FileManager
from superagi.tools.base_tool import BaseTool


class CambAIVoiceGenInput(BaseModel):
    text: str = Field(..., description="The text to be converted to speech")
    voice_id: int = Field(..., description="The ID of the voice to be used for conversion")
    language: int = Field(..., description="The language of the text to be converted to speech")
    output_file_path: str = Field(..., description="The path of the output audio file")

class CambAIVoiceGenTool(BaseTool):
    """
    CambAI Voice Generation tool

    Attributes:
        name : Name of the tool
        description : The description
        args_schema : The args schema
        resource_manager : Manages the file resources
    """
    name: str = "CambAIVoiceGenTool"
    args_schema: Type[BaseModel] = CambAIVoiceGenInput
    description: str = "A tool for converting text to speech using CambAI's voice generation API"
    resource_manager: Optional[FileManager] = None

    def _execute(self, text: str, voice_id: int, language: int, output_file_path: str):
        """
        Execute the CambAI voice generation tool.
        
        Args:
            text (str): The text to convert to speech.
            voice_id (int): The ID of the voice to use.
            output_file_path (str): The name of the output audio file.
        
        Returns:
            str: Success message or error message.
        """
        api_key = self.get_tool_config("CAMB_API_KEY")
        if api_key is None:
            return "Error: Missing CambAI API key."
        
        if voice_id is None:
            voice_id = 20303

        if language is None:
            language = 1
            
        try:
            # API base URL
            base_url = "https://client.camb.ai/apis"
            
            # Step 1: Create the TTS task
            payload = {
                "text": text,
                "voice_id": voice_id,
                "language": 1
            }
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            # Create TTS task
            response = requests.post(
                f"{base_url}/tts",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                return f"Error: Failed to create TTS task. Status code: {response.status_code}. {response.text}"
            
            data = response.json()
            task_id = data.get("task_id")
            
            if not task_id:
                return "Error: No task_id returned from Camb AI API"
            
            # Step 2: Poll for task completion
            run_id = None
            timeout_seconds = 60
            start = time.time()
            
            while True:
                if time.time() - start > timeout_seconds:
                    return "Error: Timed out waiting for TTS task to complete"
                
                status_response = requests.get(
                    f"{base_url}/tts/{task_id}",
                    headers={"x-api-key": api_key}
                )
                
                if status_response.status_code != 200:
                    return f"Error: Failed to check task status. Status code: {status_response.status_code}. {status_response.text}"
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status == "SUCCESS":
                    run_id = status_data.get("run_id")
                    break
                elif status == "FAILED":
                    return f"Error: TTS task failed. {status_data}"
                
                # Wait before checking again
                time.sleep(1)
            
            if not run_id:
                return "Error: No run_id received from completed task"
            
            # Step 3: Get the audio result
            audio_response = requests.get(
                f"{base_url}/tts-result/{run_id}",
                headers={"x-api-key": api_key},
                timeout=30
            )
            
            if audio_response.status_code != 200:
                return f"Error: Failed to get audio result. Status code: {audio_response.status_code}. {audio_response.text}"
            
            # Save the audio file
            audio_data = audio_response.content
            result = self.resource_manager.write_binary_file(output_file_path, audio_data)
            
            if result.startswith("Error"):
                return result
            
            return f"Audio file generated successfully and saved as {output_file_path}"
        except Exception as e:
            return f"Error: {str(e)}"
