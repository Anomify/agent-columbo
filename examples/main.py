from columbo.detective import Detective
import yaml

if __name__ == '__main__':

	with open('./config.yaml', 'r') as f:
		config = yaml.safe_load(f)

	detective = Detective(config)
	detective.on_duty()
