import pydantic
import typing

class DetectiveSettings (pydantic.BaseModel):

	allow_sudo: bool = pydantic.Field (
		default = False,
		description = "If enabled, allows the agent to suggest running commands with sudo privileges."
	)

	review_commands_before_executing: bool = pydantic.Field (
		default = True,
		description = (
			"If disabled, allows the agent to run all commands without user approval. "
			"Set this to `true` to prompt before each command is run."
		)
	)

	review_command_output_before_sending: bool = pydantic.Field (
		default = True,
		description = (
			"If enabled, displays command output to the user before sending to the remote server, and prompts for permission to send. "
			"When disabled, automatically sends all content to the server without user approval."
		)
	)

	command_max_output_size: int = pydantic.Field (
		default = 20000,
		description = (
			"The maximum size in bytes which is allowed to be sent to the server. "
			"If the output from an executed command is longer, the agent will attempt to run it again with tighter parameters."
		)
	)

class DetectiveConfig (pydantic.BaseModel):

	server_base_url: pydantic.HttpUrl
	api_token: str
	settings: DetectiveSettings

class ColumboRequest (pydantic.BaseModel):

	conversation_id: str | None = None
	local_datetime: str
	env_command_outputs: dict | None = None
	settings: DetectiveSettings
	content: str

class ColumboResponse (pydantic.BaseModel):

	conversation_id: str | None = None
	previous_command_stdout_relevant_excerpt: str | None = None
	completed: bool = False
	command: list[str] | None = None
	text: str | None = None

class ColumboEvidence (pydantic.BaseModel):

	conversation_id: str | None = None
	local_datetime: str | None = None
	command_stdout: str | None = None
	command_stdout_relevant_excerpt: str | None = None
	command_stderr: str | None = None
	command_code: int
	comment: str | None = None
