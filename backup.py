from boto.s3.connection import S3Connection
from botocore.exceptions import ClientError
from boto.s3.key import Key
import time
import os
from termcolor import colored
from os.path import join, abspath

class S3handler:
	"""
	Class that uploads or downloads files to s3 bucket
	"""

	def __init__(self, verbose = True):
		s3_id = os.environ['S3_ID']
		s3_secret = os.environ['S3_SECRET']
		s3_bucket = os.environ['S3_BUCKET']
		# os.environ['S3_USE_SIGV4'] = 'True'
		self.conn = S3Connection(s3_id, s3_secret)
		self.bucket = self.conn.get_bucket(s3_bucket)
		self.verbose = verbose

	def std_out(self, msg, type_message = None, force = False):
		if self.verbose or force: 
			if type_message is None: print(msg)	
			elif type_message == 'SUCCESS': print(colored(msg, 'green'))
			elif type_message == 'WARNING': print(colored(msg, 'yellow')) 
			elif type_message == 'ERROR': print(colored(msg, 'red'))

	def get_objects(self):
		objects = self.bucket.list()
		
		object_names = [obj.name for obj in objects]
		if object_names is not None:
			self.std_out(f'Successfully got keys in bucket {self.bucket.name}', 'SUCCESS')
			return object_names
		else:
			self.std_out(f'No keys in bucket {self.bucket}', 'ERROR')			
			return None

	def download(self, filename):

		filename_basename = os.path.basename(filename)
		
		self.std_out(f'Target file name: {filename_basename}')
		
		key_dest = Key(self.bucket, filename_basename)
		key_dest.get_contents_to_filename(filename)

		self.std_out(f'Downloaded files to {filename}')

	def upload(self, filename, expiration = 1296000):
		filename_basename = os.path.basename(filename)
		self.std_out(f'Target file name: {filename_basename}')

		try:
			key_dest = Key(self.bucket, filename_basename)
			key_dest.set_contents_from_filename(filename)
			response = self.conn.generate_url(expires_in= expiration, method='GET',bucket=self.bucket.name, key=filename_basename)

		except ClientError as e:
			self.std_out(e, 'ERROR')
			return None

		# The response contains the presigned URL
		self.std_out(f'Uploaded files from {filename} to {filename_basename}', 'SUCCESS')
		self.std_out(f'URL {response}')

		return response

	def delete_key(self, filename):

		filename_basename = os.path.basename(filename)
		if filename_basename in self.get_objects():
			key_dest = Key(self.bucket, filename_basename)
			self.bucket.delete_key(key_dest)
			self.std_out(f'Deleted key {key_dest} from {self.bucket.name}', 'SUCCESS')
		else:
			self.std_out('File not in bucket', 'ERROR')