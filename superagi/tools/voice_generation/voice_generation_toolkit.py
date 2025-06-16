from abc import ABC
from typing import List
from superagi.tools.base_tool import BaseTool, BaseToolkit, ToolConfiguration
from superagi.tools.voice_generation.cambai_voice_gen import CambAIVoiceGenTool
from superagi.types.key_type import ToolConfigKeyType


class VoiceGenToolkit(BaseToolkit, ABC):
    name: str = "CambAI Voice Generation Toolkit"
    description: str = "Toolkit containing tools for performing CambAI voice generation"

    def get_tools(self) -> List[BaseTool]:
        return [CambAIVoiceGenTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="CAMB_API_KEY", key_type=ToolConfigKeyType.STRING, is_required= True, is_secret = True),
        ]
