import multiprocessing
from multiprocessing import Queue
from datetime import datetime
import time
import math

class serialworker(multiprocessing.Process):

	def __init__ (self, device, buffer_length = 10, raster = 0.2, columns = [], verbose = True):

		multiprocessing.Process.__init__(self)
		self.input = Queue()
		self.output = Queue()
		self.device = device
		self.columns = columns
		# self.dataframe = df
		# self.example = df.set_index('Time')
		self.buffer_length = buffer_length
		self.verbose = verbose
		self.raster = raster

		self.std_out(f'Initialised serial worker for device on port {self.device.serialPort_name}. Buffering {self.buffer_length} samples')

	def std_out(self, msg):
		if self.verbose: print (msg)

	def run(self):
		# import pandas as pd
		# import numpy as np

		count_buffer = 0
		self.device.flush()
		last = datetime.now()

		while True:
			if not self.input.empty():

				task = self.input.get()
				print (task)

				if task == "stop":
					self.std_out('Terminating serialworker')
					self.terminate()
					self.join()
					time.sleep(0.1)
					if not self.is_alive():
						self.std_out('Time out set to 1')
						self.join(timeout=1.0)
						self.input.close()
						break

			now = datetime.now()
			data = self.device.read_line()

			if (now - last).total_seconds() > self.raster:
				last = now

				# print (data)
				# print (self.columns)
				# if 'Time' in self.columns:

				# 	if len(data) < len (self.columns): data.insert(0, pd.to_datetime(now))
				# 	else: data[0] = pd.to_datetime(data[0])
				# print (data)
				# try: data[1:] = list(map(float, data[1:]))
				# except: data[1:] = [float('nan')]; pass
				# 	print (data)
				# 	print ([data[:]])
				# 	df_stream = pd.DataFrame([data[:]], columns = self.columns)

				# print (df_stream)
				# print (data)

				# self.dataframe = pd.concat([self.dataframe, df_stream], sort=False)
				# count_buffer += 1

				# if count_buffer == self.buffer_length:
				self.output.put([self.columns, data])
				# print (self.output)
					# count_buffer = 0
					# self.dataframe = self.example