from typing import Type, Optional

from pydantic import BaseModel, Field
from cambai import CambAI
from superagi.resource_manager.file_manager import FileManager
from superagi.tools.base_tool import BaseTool


class CambAIVoiceGenInput(BaseModel):
    text: str = Field(..., description="The text to be converted to speech")
    voice_id: int = Field(..., description="The ID of the voice to be used for conversion")
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

    def _execute(self, text: str, voice_id: int, output_file_path: str):
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
        
        import os
        import tempfile
        
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, os.path.basename(output_file_path))
        
        client = CambAI(api_key=api_key)
        try:
            # Generate the audio file to the temporary location
            client.text_to_speech(
                text=text,
                voice_id=voice_id,
                save_to_file=temp_file_path
            )
            
            # Read the generated file
            with open(temp_file_path, 'rb') as file:
                audio_data = file.read()
            
            # Use resource manager to save the file
            result = self.resource_manager.write_binary_file(output_file_path, audio_data)
            
            # Clean up the temporary file
            os.remove(temp_file_path)
            
            if result.startswith("Error"):
                return result
            
            return f"Audio file generated successfully and saved as {output_file_path}"
        except Exception as e:
            return f"Error: {str(e)}"
