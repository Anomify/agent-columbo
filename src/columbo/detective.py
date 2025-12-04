import click
import colorama
import datetime
import json
import logging
import pydantic
import requests
import subprocess
import sys

# While we're working locally, to access shared models
import columbo.models

colorama.init(autoreset=True)

# Define colours

colorama_colour_command = colorama.Fore.YELLOW
colorama_colour_completed = colorama.Fore.GREEN
colorama_colour_explanation = colorama.Fore.WHITE
colorama_colour_output = colorama.Fore.YELLOW
colorama_colour_prompt = colorama.Fore.CYAN

# Set up logging

logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.ERROR)

file_handler = logging.FileHandler(
	'./debug.log',
	encoding='utf-8'
)

file_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.propagate = False

class Detective:

	"""
	The local detective acts as a proxy to Columbo, making local enquiries,
	passing them back for analysis, and receiving instructions and conclusions.
	"""

	def __init__ (self, config:dict={}):

		"""
		Initialize the detective with local config.
		"""

		try:

			self.config = columbo.models.DetectiveConfig(**config)
			self.current_conversation_id = None

		except Exception as e:

			logger.error('Init error, exiting: %s' % (e))

	def _get_datetime_string (self):

		"""
		Return a datetime string in ISO 8601 Extended Format
		"""

		dt_local = datetime.datetime.now().astimezone()

		return dt_local.isoformat()

	def _run_local_command (self, command:list[str]) -> tuple[str, str, int]:

		"""
		Run a local command using `subprocess.Popen` to enforce output limits safely.
		This is safer than `subprocess.run`
		"""

		stdout_accumulator = []
		current_size = 0

		try:

			with subprocess.Popen(
				command,
				stdout = subprocess.PIPE,
				stderr = subprocess.PIPE,
				text = True,
				bufsize = 1,
			) as process:

				for line in process.stdout:

					stdout_accumulator.append(line)
					current_size += len(line)

					if current_size > self.config.settings.command_max_output_size:
						process.kill()
						break

				_, stderr_output = process.communicate()

				return (
					"".join(stdout_accumulator).strip(), 
					stderr_output.strip(), 
					process.returncode
				)

		except Exception as e:

			logger.error("Execution error: %s" % (e))
			return ("", str(e), 1)

	def _run_local_command_old (self, command:list[str]) -> tuple:

		"""
		Run a local command, returning (stdout, stderr, return code)
		"""

		result = subprocess.run(command, capture_output=True, text=True)

		return (result.stdout.strip(), result.stderr.strip(), result.returncode)

	def _confirm_run_local_command (self, command:list[str]) -> tuple:

		"""
		Get user confirmation to run a command, if that is required.
		Then call _run_local_command()
		"""

		print(colorama_colour_command + '\n' + '> ' + ' '.join(command))

		comment = None

		# Check for sudo

		if not self.config.settings.allow_sudo and command[0] == 'sudo':

			logger.error('Model attempted sudo.')
			return None, None, 1, 'You are not permitted to use `sudo`.'

		if not self.config.settings.review_commands_before_executing:

			ok_to_run = True

		else:

			# Get confirmation to run the command if we need it.

			keypress_options = {'y': 'Yes', 'n': 'No', 'x': 'Exit'}

			keypress = self._get_prompt_keypress("\n" + 'OK to run this command?', keypress_options)

			if keypress == 'x':
				print('Exiting')
				sys.exit(1)

			ok_to_run = True if keypress == 'y' else False

		if ok_to_run:

			cmd_stdout, cmd_stderr, cmd_code = self._run_local_command(command)

			if len (cmd_stdout) > self.config.settings.command_max_output_size:

				cmd_stdout, cmd_stderr, cmd_code = (None, None, 1)

				comment = (
					'The output of the command exceeded the maximum length defined by the user. '
					'Try an alternative command or options to reduce the output size.'
				)

		else:

			cmd_stdout, cmd_stderr, cmd_code = (None, None, 1)
			comment = 'The user declined to allow the command to run. Try something else.'

		return cmd_stdout, cmd_stderr, cmd_code, comment

	def _get_env_command_outputs (self) -> dict:

		"""
		Run some local commands to provide background information on the server.
		"""

		commands = [
			['cat','/etc/os-release'],
			['uname','-a'],
		]

		env_command_outputs = {}

		for command in commands:

			(command_output, _, _) = self._run_local_command(command)

			command_string = ' '.join(command)

			env_command_outputs[command_string] = command_output

		return env_command_outputs

	def _get_prompt_keypress (self, prompt:str, keypress_options:dict):

		"""
		Prompt the user for a keypress response. It must be one of the valid options.
		Return the valid character.
		"""

		valid_keys = keypress_options.keys()

		valid_char_str = ' / '.join(["%s (%s)" % (v, k) for k, v  in keypress_options.items()])

		keypress = None

		while keypress not in valid_keys:

			print(colorama_colour_prompt + '%s [%s]: ' % (prompt, valid_char_str), end='', flush=True)
			keypress = click.getchar().lower()
			print(keypress)

		return keypress

	def _get_server_url (self, method:str):

		return str(self.config.server_base_url).rstrip('/') + '/' + method.strip('/')

	def _run_slash_command (self, command:list[str]):

		"""
		Execute a remote API call.
		"""

		valid_commands = ['delete']

		if command[0] not in valid_commands:

			print(colorama_colour_explanation + '"%s" is not a valid command.' % (command[0]))
			return False

		command_api_url = self._get_server_url(requests.utils.quote(command[0]))

		if len(command) > 1:
			command_api_url += '/' + '/'.join([requests.utils.quote(c) for c in command[1:]])

		print(colorama_colour_explanation + "Attempting to execute remote API call:")

		print(colorama_colour_command + command_api_url)

		headers = {
			'Authorization': 'Bearer %s' % (self.config.api_token)
		}

		http_response = requests.post(command_api_url, headers=headers)

		if 200 <= http_response.status_code < 300:

			print(colorama_colour_explanation + "Remote API call executed successfully :)")

			if command[0] == 'delete' and len(command) > 1 and command[1] == self.current_conversation_id:
				# We have deleted the current conversation. So reset the local id.
				self.current_conversation_id = None

			return True

		if 400 <= http_response.status_code < 500:

			print(colorama_colour_explanation + "Remote API reported a client error (%d)" % (http_response.status_code))
			return False

		if 500 <= http_response.status_code < 600:

			print(colorama_colour_explanation + "Remote API reported a server error (%d)" % (http_response.status_code))
			return False

		print(colorama_colour_explanation + "Remote API call failed with error code %d" % (http_response.status_code))

		return False

	def investigate (self, issue:str):

		"""
		Investigate an issue.
		"""

		try:

			# Setup

			headers = {
				'Authorization': 'Bearer %s' % (self.config.api_token)
			}

			env_command_outputs = self._get_env_command_outputs()

			payload_dict = {
				'conversation_id': self.current_conversation_id,
				'local_datetime': self._get_datetime_string(),
				'env_command_outputs': env_command_outputs,
				'settings': self.config.settings,
				'content': issue,
			}

			# Validate
			payload_dict = columbo.models.ColumboRequest(**payload_dict).model_dump()

			http_response = requests.post(
				self._get_server_url('investigate'),
				json = payload_dict,
				headers = headers,
				stream = False,
				timeout = (5, 30)
			)

			http_response.raise_for_status()

			http_response_dict = json.loads(http_response.json())

			columbo_response = columbo.models.ColumboResponse(**http_response_dict)

			if self.current_conversation_id is None:

				print(colorama_colour_output + "The id for this conversation is %s." % (columbo_response.conversation_id))
				print(colorama_colour_output + "You may delete this conversation from our server at any time by entering the following at the issue prompt: /delete %s" % (columbo_response.conversation_id))

			self.current_conversation_id = columbo_response.conversation_id

		except requests.exceptions.ConnectionError:

			print(colorama_colour_output + "Cannot connect to the remote service. Exiting.")
			sys.exit(1)

		except requests.exceptions.HTTPError as e:

			print(colorama_colour_output + "The remote service reported an error. Exiting. (\"%s\")" % (e))
			sys.exit(1)

		except Exception as e:

			print(colorama_colour_output + "Something went wrong setting up the conversation. We'll stop here for now.")
			sys.exit(1)

		try:

			while True:

				# Loop through processing response and making next request
				# until the investigation is completed.

				if columbo_response.text:

					print("\n" + colorama_colour_explanation + columbo_response.text)

				if columbo_response.completed:

					print(colorama_colour_completed + "\n*** CASE CLOSED ***\n")
					break

				if not columbo_response.command:

					logger.error('No command specified')
					break

				completed = columbo_response.completed

				cmd_stdout, cmd_stderr, cmd_code, comment = self._confirm_run_local_command(columbo_response.command)

				# Trim responses if required

				cmd_stdout = cmd_stdout if cmd_stdout is None else cmd_stdout.strip() 
				cmd_stderr = cmd_stderr if cmd_stderr is None else cmd_stderr.strip() 

				if self.config.settings.review_command_output_before_sending:

					# User must review output from the command before sending.

					cmd_output_display = cmd_stdout if cmd_stdout else "[no output]"

					print(colorama_colour_output + "\n" + cmd_output_display + "\n")

					keypress_options = {'y': 'Yes', 'n': 'No'}

					keypress = self._get_prompt_keypress('OK to send this output to the server?', keypress_options)

					if keypress == 'n':
						cmd_stdout, cmd_stderr = (None, None)
						comment = 'The user declined to allow the output of the command to be sent.'

				payload_dict = {
					'conversation_id': self.current_conversation_id,
					'local_datetime': self._get_datetime_string(),
					'command_stdout': cmd_stdout,
					'command_stderr': cmd_stderr,
					'command_code': cmd_code,
					'comment': comment,
				}

				payload_dict = columbo.models.ColumboEvidence(**payload_dict).model_dump()

				http_response = requests.post(self._get_server_url('evidence'), json=payload_dict, headers=headers, stream=False)

				http_response.raise_for_status()

				http_response_dict = json.loads(http_response.json())

				columbo_response = columbo.models.ColumboResponse(**http_response_dict)

		except requests.exceptions.ConnectionError:

			logger.error('Could not connect to server')

		except requests.exceptions.HTTPError as e:

			logger.error('Server error: %s' % (e))

		except json.JSONDecodeError:

			logger.error("Response is not valid JSON: %s" % (http_response.text))

		except pydantic.ValidationError:

			logger.error("Response does not match the expected model: %s" % (http_response.text))

		except Exception as e:

			logger.error('An unknown error occurred: %s' % (e))

	def on_duty (self):

		while True:

			print(colorama_colour_prompt + "What would you like me to investigate?")

			issue = input(colorama_colour_prompt + 'Issue: ').strip()

			if len(issue):

				if issue[0] == '/':

					self._run_slash_command(issue[1:].split())
					continue

				self.investigate(issue)
