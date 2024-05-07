# -*- coding: utf-8 -*-
"""Event-based- Vectrust A3C for TF2.3.1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BJ5E8_ETEuuVOdly6pYjm-tEmwWiYIy1
"""
import random
random.seed(2023)
VENCOUNT = 3

def recursive_str(d):
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = recursive_str(value)
        else:
            d[key] = str(value)
    return d

#users
class User:
    def __init__(self, name, ID):
        self.name = name
        self.ID = ID
        self.submitted_workflows = {}

    def __str__(self):
        return str(self.__dict__)

#workflows
from collections import namedtuple
#QSpec = namedtuple('Qspec', ['req_cores', 'req_ram', 'req_time'])
SSpec = namedtuple('Sspec', ['AC', 'CA', 'IA', 'SC', 'SI'])
class Workflow:
    def __init__(self, name, req_ram, req_cores, req_time, ac, ca, ia, sc, si):
        self.name = name
        self.SSpec = SSpec(AC=ac, CA=ca, IA=ia, SC=sc, SI=si)
        
    def __str__(self):
        copy_dict = self.__dict__.copy()
        recursive_dict = recursive_str(copy_dict)
        return str(recursive_dict)

#vens
RSpec = namedtuple('RSpec', ['cpu_speed','number_of_cores','ram', 'storage', 'AC', 'CA', 'IA', 'SC', 'SI'])
class VEN:
    preference_list_max_size = 10
    queue_capacity = 5 #maximum size of queue
    queue_time_capacity = 3600 #seconds
    def __init__(self, owner_name, ID, cpu_speed, number_of_cores, ram, storage, ac, ca, ia, sc, si, preference_list, config):
        self.name = owner_name
        self.ID = ID
        self.RSpec = RSpec(cpu_speed=cpu_speed, number_of_cores=number_of_cores, ram=ram, storage=storage, \
                            AC=ac, CA=ca, IA=ia, SC=sc, SI=si)
        self.preference_list = {}
        self.set_preference_list(preference_list)
        self.queue = []
        self.queuesize = 0
        self.preference_list_size = 0
        self.trust = 1
        self.config = config

    def set_preference_list(self, preference_list):
        self.preference_list.clear()
        for i, ID in enumerate(preference_list):
            self.preference_list[ID] = i+1
        self.preference_list_size = len(self.preference_list)

    def get_rank_of(self, ID):
        return self.preference_list[ID] if ID in self.preference_list.keys() else None

    def add_to_queue(self, job):
        if self.queuesize<self.queue_capacity:
          self.queue.append(job)
          self.queuesize += 1
          job.simulate_actual_exe_time()
          job.assigned_to = self
        else:
          job.assigned_to = "rejected"

    def update_trust(self, job):
        mismatch = (job.finished_at - job.submitted_at) - job.expected_exe_time
        update = 0 if mismatch <=0 else -(0.0001)*(mismatch/job.expected_exe_time)
        self.trust = max(0, self.trust+update) if self.trust+update<1 else min(self.trust+update, 1)
        if self.trust < 0:
          raise Exception(mismatch, update, "trust value", self.trust)

    def job_is_done(self, job):
        self.update_trust(job)
        self.queue.remove(job)
        self.queuesize -= 1

    def clear_queue(self):
      self.queue.clear()
      self.queuesize = 0

    def __str__(self):
        copy_dict = self.__dict__.copy()
        recursive_dict = recursive_str(copy_dict)
        return str(recursive_dict)

#jobs
from collections import namedtuple
QSpec = namedtuple('Qspec', ['required_delay'])
class Job:
    # delaydata = {'RNASeq':{1:34, 4:56, 16:120}, 'PGen':{1:12, 4:30 , 16:80}}
    #delaydata = {'RNASeq':{1:34, 2:45, 3:56}, 'PGen':{1:12, 2:18 , 3:24}}
    delaydata = {'RNASeq':{1:14, 2:25, 3:36}, 'PGen':{1:6, 2:12 , 3:24}}
    def __init__(self, workflow_name=None, userID=None, submission_time=None, data=None):
      self.workflow_type = workflow_name
      self.userID = userID
      self.submitted_at = submission_time
      self.finished_at = None
      self.data = data
      self.data_size = self.data_size()
      self.actual_exe_time = 0
      self.expected_exe_time = 0
      self.log = ""
      self.cores_at_clock_instance = []
      self.queue_time = 0
      self.QSpec = QSpec(required_delay = self.delay_estimation()) if workflow_name else None
      self.ss = None
      self.qs = None
      self.vens = None 
      self.assigned_to = None

    def data_size(self):
      return self.data #in simulation data is same as size, in implementation one is address of data the other is size

    def delay_estimation(self):
      return Job.delaydata[self.workflow_type][self.data_size]

    # def set_expected_exec_time(self,vm):
    #   self.expected_exec_time = self.req_cpu_and_time/vm.cores
    #   self.log+=self.name+" assigned to "+vm.name+"("+str(vm.cores)+")\nexpected time:" + str(self.expected_exec_time)+"\n"
    
    def set_expected_exe_time(self, ven):
        ven_config = ven.config
        ven_effective_speed = VECEnv.effectivespeeddata[self.workflow_type][ven_config]
        estimate = self.data_size/float(ven_effective_speed)
        self.expected_exe_time = estimate
        return self.expected_exe_time

    def simulate_actual_exe_time(self):
        margin = 0.1 * self.expected_exe_time
        noise = noise = np.random.uniform(-margin, margin)
        self.actual_exe_time = self.expected_exe_time + noise
        self.finished_at = self.submitted_at + self.queue_time + self.actual_exe_time #add local queue time

    def __gt__(self, other):
        if isinstance(other, Job):
            return self.submitted_at >= other.submitted_at
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Job):
            return self.submitted_at < other.submitted_at
        return NotImplemented

    def get_summary_completion(self):
        return f"req workload: {self.req_cpu_and_time} \ncores at clock instance: {self.cores_at_clock_instance}"
    
    def updatess(self, ss):
        self.ss = ss

    def __str__(self):
        copy_dict = self.__dict__.copy()
        recursive_dict = recursive_str(copy_dict)
        return str(recursive_dict)+"\n"

"""**Simulation**"""
def load_workflows(): #load_workflows - considering unique names
  workflows = {}
  flag = True
  with open('workflow.csv', 'r') as wff:
    for line in wff:
      if flag:
        flag = False
        continue
      line = line.replace("\n","").split(",")
      name = line[0]
      req_ram, req_cores, req_time = line[1:4]
      ac, ca, ia, sc, si = line[4:]
      workflows[name] = Workflow(name, int(req_ram), int(req_cores), int(req_time), ac, ca, ia, sc, si )
  return workflows

def generate_users(token, number_of_users): #generate random users and assigns unique ID to them
  if token=="generate":
    
    users = []
    '''
    IDS = set()

    # Load list of 20 first names and 20 last names and creat all possible combinations
    import random
    random.seed(2023)
    first_names = ['Emma', 'Liam', 'Sofia', 'Benjamin','Ava', 'Mason', 'Mia',\
            'Elijah', 'Charlotte', 'William', 'Amelia', 'James', 'Harper',\
            'Alexander', 'Madison', 'Ethan', 'Isabella', 'Michael', 'Abigail', 'Daniel']
    last_names = ['Smith', 'Johnson', 'Brown', 'Garcia', 'Davis', 'Rodriguez',\
              'Miller', 'Martinez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas',\
              'Taylor', 'Moore', 'Jackson', 'Lee', 'Perez', 'Hall', 'Young', 'King']
    full_names = [f+' '+l for f in first_names for l in last_names]

    # Generate 20 random name pairs
    random.shuffle(full_names)
    for name in full_names[:number_of_users]:
      _id = str(random.randint(100000, 999999))
      while _id in IDS:
        _id = str(random.randint(100000, 999999))
      else:
        IDS.add(_id)
      users.append(User(name, _id))
      # with open("simulationusers.txt", 'w') as persist:
      # 	for user in users:
      # 		persist.write(user.__str__()+"\n")
    # for u in users:
    #   print(u)
    # print(IDS)'''
    IDS = ['328218','161598','932598','319481','133056']
    names = ['Mason Garcia', 'Ava Young', 'Alexander Hall', 'Mia Rodriguez', 'Benjamin Hall']
    for pair_ in zip(names, IDS):
        users.append(User(pair_[0], pair_[1]))
    
    return users, IDS

def generate_arrival_times(start_time, end_time): #generating arival times of jobs based on Poisson distribution
	import numpy as np
	np.random.seed(2023)

	lam = 0.2 #1.6  # mean arrival rate per minute #I used timeslot over queue size
	interval = 1  # time interval in minutes

	# generate a sequence of inter-arrival times based on exponential distribution
	times = np.cumsum(np.random.exponential(1/lam, int((end_time-start_time)/interval)))

	# convert inter-arrival times to arrival times
	arrival_times = [start_time + int(t) for t in times if start_time + int(t) <= end_time]
	return arrival_times

def generate_jobs(workflows, users, start_time, end_time): #generating jobs
  jq = []
  arrival_times = generate_arrival_times(start_time, end_time) #based on poisson
  for at in arrival_times:
    jq.append(Job(random.choice(list(workflows.values())).name, random.choice(users).ID, at, random.choice([1, 2, 3])))
  return jq

def generate_vens(IDS, number_of_vens):
        print("~~~~~~~~~~~~~~~~~~HERE~~~~~~~~~~")
        #random.seed(2023)
        vens = []
        userIDS = list(IDS)

        cpu_speed = [1.1, 1.3, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.6, 4.8, 5.0]
        number_of_cores = [1, 2, 4, 6, 8, 10, 12, 16]
        ram= [2, 4, 8, 16, 32, 64, 128]
        storage = [128, 256, 512, 1024, 2048, 4096]
        security_factor = ['L', 'M', 'H']

        first_names = ['Emma', 'Liam', 'Sofia', 'Benjamin','Ava', 'Mason', 'Mia',\
						'Elijah', 'Charlotte', 'William', 'Amelia', 'James', 'Harper',\
						'Alexander', 'Madison', 'Ethan', 'Isabella', 'Michael', 'Abigail', 'Daniel']
        last_names = ['Smith', 'Johnson', 'Brown', 'Garcia', 'Davis', 'Rodriguez',\
					 'Miller', 'Martinez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas',\
					  'Taylor', 'Moore', 'Jackson', 'Lee', 'Perez', 'Hall', 'Young', 'King']
        full_names = [f+' '+l for f in first_names for l in last_names]

        venIDS = set()
        vens = []
        flag = True
        with open("ven.csv",'r') as venf:
            for line in venf:
                print(line)
                if flag:
                    flag = False
                    continue
                name = random.choice(full_names)
                _id = random.randint(100000, 999999)
                while _id in venIDS:
                        _id = random.randint(100000, 999999)
                else:
                        venIDS.add(_id)
                #generate preference list
                list_size = 5 #random.randint(0, 10) #generate size of preference list
                #random.shuffle(userIDS)
                config, AC, CA, IA, SC, SI = line.replace("\n","").split(",")[:6]
                preference_list = line.replace("\n","").split(",")[6:]
                vens.append(VEN(name, _id, random.choice(cpu_speed), random.choice(number_of_cores), random.choice(ram), \
					random.choice(storage), AC, CA, IA, SC, SI, \
					preference_list,config))
        return vens

def simulation_environment(number_of_users=5, number_of_vens=VENCOUNT): #creating components of the simulations
  #loading workflows from workflows.csv
  workflows = load_workflows()
  users, IDS = generate_users("generate", number_of_users)
  jobs = generate_jobs(workflows, users, start_time = 0, end_time = 3600) #start time used to be 1000 before #3600
  vens = generate_vens(IDS, number_of_vens)

  return workflows, users, jobs, vens, IDS

'''def simulator():
  workflows, users, jobs, vens = simulation_environment()
  #workflow and users should be in form of dict based on name and userID
  systemtime = 1000
  time_slot_duration = 30 #\s
  JQcapacity = 6
  job_pointer = 0
  jq = []
  print("jobs", jobs)
  for time in range(systemtime, systemtime+1000, time_slot_duration): # the entire steps of the simulation
    while job_pointer<len(jobs) and jobs[job_pointer].submission_time <= time\
        and len(jq)<JQcapacity :
      jq.append(jobs[job_pointer])
      job_pointer+=1
  # allocation(jq, VENs, workflows, users, jobs, vens)
'''

"""Reinforcement Learning

Creating the gym environment
"""
import gym
from gym import spaces
import numpy as np
import math
import heapq

class VECEnv(gym.Env):
    #effectivespeeddata = {'RNASeq': {'config1':20, 'config2':32, 'config3':40}, 'PGen':{'config1':8, 'config2':12, 'config3':16}} #GB per second
    effectivespeeddata = {'RNASeq': {'config1':0.05, 'config2':0.3, 'config3':0.7}, 'PGen':{'config1':0.1, 'config2':0.4, 'config3':0.9}} #GB per second
    def __init__(self, number_of_vens=VENCOUNT , current_queue_size = 1, number_of_workflows = 2, number_of_users = 5):
        self.workflows, self.users, self.jobs, self.vens, self.userIDs = simulation_environment()
        self.job = []
        self.processing_q = []
        self.number_of_vens = number_of_vens
        self.number_of_workflows = number_of_workflows
        self.number_of_users = number_of_users
        #self.queue_size = queue_size
        self.rem_step = 1
        self.time_slot_duration = 10
        self.data_size_count = 2
        self.capacity_mode_count = 4 #0,1,2,3
        #print("Objects")   
        #for w in self.workflows:     
        #    print(w, str(self.workflows[w]))
        #for u in self.users:	     
        #    print(str(u))
        #for v in self.vens:	     
         #   print(str(v))
        #for j in self.jobs:	     
         #   print(str(j))

        #4 states of vens queues (considering size of queue is 6) are L(0-1), M(2-3), H(4), F(full  = 5)
        '''defining states as the level of the occupancy of vens' queue (L:0, M:1, H:2, F:3) and\\
        then the type of the workflows in job queue and its current size'''

        observation_space = [self.number_of_workflows+1, self.data_size_count+1, self.number_of_users+1]+[self.capacity_mode_count for i in range(self.number_of_vens)]
        self.observation_space = spaces.MultiDiscrete(observation_space)
        self.action_space = spaces.Discrete(number_of_vens+1) # MultiDiscrete([number_of_vens+1 for i in range(queue_size)])
        self.state = [0, 0, 0]+[0 for i in range(self.number_of_vens)]

    def jobsetter(self, job):
      self.job = job

    def reset(self):
        one_state = np.array([0,0,0]+[0 for i in range(self.number_of_vens)])
        self.state = np.array([one_state for i in range(self.rem_step)])
        self.state = np.expand_dims(self.state, axis=0)
        return self.state

    def update_state_jq(self, state): #update state based on job queue
      if self.job:
        if self.job.workflow_type=="RNASeq":
          state[0][0][0] = 1
          state[0][0][1] = self.job.data_size
          state[0][0][2] = self.userIDs.index(str(self.job.userID))+1
        elif self.job.workflow_type=="PGen":
          state[0][0][0] = 2
          state[0][0][1] = self.job.data_size
          state[0][0][2] = self.userIDs.index(str(self.job.userID))+1
        else:
          print(self.job.workflow_type)
          state[0][0][0] = 0
          state[0][0][1] = 0
          state[0][0][2] = 0

        #local queue L:0, M:1, H:2, F:3
        #L: 0-1 M: 2-3 H: 4 F: 5
        for i in range(len(self.vens)):
          q_size = self.vens[i].queuesize
          if q_size in [0]:
            state[-1][-1][i+3] = 0
          elif q_size in [1,2]:
            state[-1][-1][i+3] = 1
          elif q_size in [3,4]:
            state[-1][-1][i+3] = 2
          else:
            state[-1][-1][i+3] = 3
      return state

    def update_state(self, action, state): #upade state based on action [they might need to be merged]
        new_state = np.hstack((np.array([0, 0]), state[0][0][2:]))
        ven = action
        if ven:
          if not self.job.expected_exe_time:
            self.job.set_expected_exe_time(self.vens[ven-1])
          self.vens[ven-1].add_to_queue(self.job) #ven-1 because 0 is reserved for not assigned

          if self.job.assigned_to != 'rejected':
            heapq.heappush(self.processing_q, (self.job.finished_at, self.job))

        #local queue L:0, M:1, H:2, F:3
        #L: 0-1 M: 2-3 H: 4 F: 5
        for i in range(len(self.vens)):
          q_size = self.vens[i].queuesize
          if q_size==0:
            new_state[3+i] = 0
          elif q_size in [1,2]:
            new_state[3+i] = 1
          elif q_size in [3,4]:
            new_state[3+i] = 2
          else:
            new_state[3+i] = 3

        state[0] = np.roll(state[0], 1, axis = 0)
        state[0,0,:] = new_state
        return state

    def security_satisfaction(self, job, ven):
        sspec = self.workflows[job.workflow_type].SSpec
        rspec = ven.RSpec
        res = []
        function = math.sqrt
        for factor in sspec._fields:
          if getattr(sspec, factor) == getattr(rspec, factor):
            res.append(function(1))
          elif (getattr(sspec,factor)=='L' and getattr(rspec,factor)=='M')\
              or (getattr(sspec,factor)=='M' and getattr(rspec,factor)=='H'):
            res.append(function(2/3))
          elif getattr(sspec,factor)=='L' and getattr(rspec,factor)=='H':
            res.append(function(1/3))
          else:
            res.append(0)
        #print("result---->", res)
        return min(res)

    def Q_satisfaction(self, job, ven):
        # workflow_type, data_size = job.workflow_type, job.data_size

        # #delay estimate
        # ven_config = ven.config
        # ven_effective_speed = VECEnv.effectivespeeddata[workflow_type][ven_config]
        # delay_estimate = data_size/ven_effective_speed
        # job.expected_exe_time = delay_estimate
        required_delay = job.delaydata[job.workflow_type][job.data_size]
        ven_queue_time =  sum([existing.expected_exe_time for existing in ven.queue])
        delay_estimate = job.set_expected_exe_time(ven) + ven_queue_time
        job.queue_time +=  ven_queue_time
        delta = required_delay - delay_estimate
        return 1/(1+math.exp(-delta)) if delta>=0 else (0.3)*math.tanh(delta)

    def workflow_satisfaction(self, ven):
        c1 = 1
        c2 = 1
        ss = self.security_satisfaction(self.job, ven)
        self.job.updatess(ss)  
        if not ss:
          return 0
        qs = self.Q_satisfaction(self.job, ven)
        self.job.qs = qs
        return c1*ss + c2*qs

    def ven_satisfaction(self, ven):
        if self.job.userID in ven.preference_list.keys():
          print("|| ", self.job.userID, type(self.job.userID))
          print(ven.preference_list)
          vens = (-1/6)*math.log(int(ven.preference_list[self.job.userID]))+1
          self.job.vens = vens
          return vens  
        self.job.vens = 0     
        return 0

    def reward_calculation(self, action):
        print("Reward calculation ")
        reward = 0.0
        a1 = 0.5
        a2 = 0.5
        b = 0.1
        if self.job.workflow_type:
          ven = action
          VEN = self.vens[ven-1] #ven-1 because 0 is reserved for not assigned
          if ven !=0 :
            ws = self.workflow_satisfaction(VEN)
            vs = self.ven_satisfaction(VEN)
            reward = a1*VEN.trust*ws + a2*vs if ws>0 else 0.001
          else:
            if sum([v.queuesize for v in self.vens])==sum([v.queue_capacity for v in self.vens]):
              reward = 0.0001
            else:
              reward = -0.5
            self.job.assigned_to = 'rejected'
        return reward

    def step(self, action):
        done = False
        assert self.action_space.contains(action)
        print("state ", self.state)
        print("action ", action)
        reward = 0.0

        if action and self.vens[action-1].queuesize == self.vens[action-1].queue_capacity: #ven-1 because 0 is reserved for no-assignment
            reward = -1.0
        else:
          reward = self.reward_calculation(action)

        self.state = self.update_state(action, self.state) #it used to be only state without self
        # if self.state[0] > 1.0:
        #     reward = 1.0
        #     done = True
        #reward = (reward - (-1)) / ((1.5) - (-1))
        print('reward :::', reward)
        if reward < -1:
          raise Exception("WHY THIS VALUE? ", reward)
        return (self.state, reward, done, {})

    def render(self, mode='human'):
        print(self.state)

gym.register(id='VECEnv-RS', entry_point='__main__:VECEnv')

"""**Learning**"""

import os
#os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
import random
import gym

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

#import pylab

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Dense, Lambda, Add, Conv2D, Flatten
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras import backend as K
import cv2
import threading
from threading import Thread, Lock
import time

gpus = tf.config.experimental.list_physical_devices('GPU')
if len(gpus) > 0:
    raise Exception(f'GPUs {gpus}')
    print(f'GPUs {gpus}')
    try: tf.config.experimental.set_memory_growth(gpus[0], True)
    except RuntimeError: pass

# Create a custom callback to print activations at each layer during training
class ActivationPrintCallback(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        print("Epoch:", epoch)
        for i, layer in enumerate(self.model.layers):
            activation = layer.get_weights()
        print()

def OurModel(input_shape, action_space, lr):
    X_input = Input(input_shape)

    #X = Conv2D(32, 8, strides=(4, 4),padding="valid", activation="elu", data_format="channels_first", input_shape=input_shape)(X_input)
    #X = Conv2D(64, 4, strides=(2, 2),padding="valid", activation="elu", data_format="channels_first")(X)
    #X = Conv2D(64, 3, strides=(1, 1),padding="valid", activation="elu", data_format="channels_first")(X)
    X = Flatten(input_shape=input_shape)(X_input)

    X = Dense(512, activation="elu", kernel_initializer='he_uniform')(X)
    #X = Dense(256, activation="elu", kernel_initializer='he_uniform')(X)
    #X = Dense(64, activation="elu", kernel_initializer='he_uniform')(X)

    action = Dense(action_space, activation="softmax", kernel_initializer='he_uniform')(X)
    value = Dense(1, kernel_initializer='he_uniform')(X)

    Actor = Model(inputs = X_input, outputs = action)
    #Actor.load_weights('eventbasedinitials_Actor_initial.h5')
    Actor.compile(loss='categorical_crossentropy', optimizer=RMSprop(learning_rate=lr))

    Critic = Model(inputs = X_input, outputs = value)
    #Critic.load_weights('eventbasedinitials_Critic_initial.h5')
    Critic.compile(loss='mse', optimizer=RMSprop(learning_rate=lr))
    
    #initial_weights = Actor.get_weights()
    #for layer_weights in initial_weights:
    #    print(layer_weights)

    return Actor, Critic

import traceback

def process_exception(exception):
    print("Exception Handling function which is mine")
    # Extract the exception message
    exception_message = str(exception)

    # Get the traceback information
    traceback_info = traceback.format_exc()

    # Construct links or relevant information
    link1 = "[Link 1](https://example.com/exception1)"
    link2 = "[Link 2](https://example.com/exception2)"

    # Create a formatted message with links
    formatted_message = f"{exception_message}\n\nTraceback:\n{traceback_info}\n\nLinks:\n{link1}\n{link2}"
    print("the error detail ", formatted_message)
    # Raise a new exception with the formatted message
    raise Exception(formatted_message)


class A3CAgent:
    # Actor-Critic Main Optimization Algorithm
    exception_event = threading.Event()
    def __init__(self, env_name='VECEnv-RS', queue_size = 3, number_of_vens = VENCOUNT):
        # Initialization
        # Environment and PPO parameters
        self.env_name = env_name
        self.env = gym.make(env_name)
        print('number of jobs ', len(self.env.jobs))
        self.action_size = self.env.action_space.n
        self.EPISODES, self.episode, self.max_average = 1000, 0, -1 #20000, 0, -21.0 # specific for pong
        #self.EPISODES, self.episode, self.max_average = 20000, 0, -21.0 # specific for pong
        self.lock = Lock()
        self.lr = 0.0001#0.01#0.001#0.000025

        self.ROWS = 3 + number_of_vens
        #self.COLS = 80
        self.REM_STEP = 1

        # Instantiate plot memory
        self.scores, self.episodes, self.average = [], [], []

        self.Save_Path = f'Models_{VENCOUNT}_{self.lr}'
        self.state_size = (self.REM_STEP, self.ROWS)#, self.COLS)

        if not os.path.exists(self.Save_Path): os.makedirs(self.Save_Path)
        self.path = '{}_A3C_{}'.format(self.env_name, self.lr)
        self.Model_name = os.path.join(self.Save_Path, self.path)

        # Create Actor-Critic network model
        self.Actor, self.Critic = OurModel(input_shape=self.state_size, action_space = self.action_size, lr=self.lr)

    def on_epoch_end(self, epoch, logs=None):
        print("Epoch:", epoch)
        for i, layer in enumerate(self.actor.layers):
            activation = layer.output
            print("Layer", i+1, "Activation:", activation)
        print()

    def validaction(self, state, action):
        #print(action)
        for index in range(len(action)):
          if state[0][0][index]==0 and action[index]!=0:
            return False
        return True
    def act(self, state):
        # Use the network to predict the next action to take, using the model
        #temp = self.Actor.predict(state)
        #print(len(temp), type(temp), temp)
        prediction = self.Actor.predict(state)[0]
        print("prediction ",prediction)

        # Motahare added this to replace NaN values with 0
        #prediction[np.isnan(prediction)] = 0

        if np.count_nonzero(np.isnan(prediction))!=0:
          print(" ^^^^^^^^^^^^^^^ NaN values ",np.count_nonzero(np.isnan(prediction)), len(prediction))

        action = np.random.choice(self.action_size, p=prediction)
        #details = self.env.action_dict[action]

        #counter = 0
        # while not self.validaction(state, details):
        #   print("repeat ", state, action)
        #   action = np.random.choice(self.action_size, p=prediction)
        #   details = self.env.action_dict[action]
        #   counter += 1

        return action

    def discount_rewards(self, reward):
        # Compute the gamma-discounted rewards over an episode
        gamma = 0.01 #0.99    # discount rate
        running_add = 0
        discounted_r = np.zeros_like(reward, dtype=np.float64)
        for i in reversed(range(0,len(reward))):
            # if reward[i] != 0: # reset the sum, since this was a game boundary (pong specific!)
            #     running_add = 0
            running_add = running_add * gamma + reward[i]
            discounted_r[i] = running_add
        print("discounted_r : ", discounted_r)
        print('reward ', reward)
        #print('discounted_r', len(discounted_r), discounted_r, np.mean(discounted_r))
        discounted_r -= np.mean(discounted_r, dtype=np.float64) # normalizing the result
        print('discounted_r', len(discounted_r), discounted_r, np.std(discounted_r))

        discounted_r /= np.std(discounted_r) # divide by standard deviation
        return discounted_r

    def replay(self, states, actions, rewards):
        # reshape memory to appropriate shape for training
        states = np.vstack(states)
        actions = np.vstack(actions)

        # Compute discounted rewards
        discounted_r = self.discount_rewards(rewards)

        # Get Critic network predictions
        value = self.Critic.predict(states)[:, 0]
        # Compute advantages
        advantages = discounted_r - value
        # training Actor and Critic networks
        #for i in range(len(states)):
        #  print(states[i],"\t",actions[i],"\t", advantages[i])
        self.Actor.fit(states, actions, sample_weight=advantages, epochs=1, verbose=0)#, callbacks=[ActivationPrintCallback()])
        self.Critic.fit(states, discounted_r, epochs=1, verbose=0)

    def load(self, Actor_name, Critic_name):
        self.Actor = load_model(Actor_name, compile=False)
        self.Critic = load_model(Critic_name, compile=False)

    def save(self):
        self.Actor.save(self.Model_name + '_Actor.h5')
        self.Critic.save(self.Model_name + '_Critic.h5')

    plt.figure(figsize=(18, 9))
    def PlotModel(self, score, episode):
        self.scores.append(score)
        self.episodes.append(episode)
        self.average.append(sum(self.scores[-50:]) / len(self.scores[-50:]))
        if str(episode)[-2:] == "00":# much faster than episode % 100
            plt.plot(self.episodes, self.scores, 'b')
            plt.plot(self.episodes, self.average, 'r')
            plt.ylabel('Score', fontsize=18)
            plt.xlabel('Steps', fontsize=18)
            try:
                plt.savefig(self.path+".png")
            except OSError:
                pass

        return self.average[-1]

    def imshow(self, image, rem_step=0):
        cv2.imshow(self.Model_name+str(rem_step), image[rem_step,...])
        if cv2.waitKey(25) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            return

    def reset(self, env):
        state = env.reset()
        return state

    def step(self, action, env, state):
        x = env.step(action)#(action, state))dtype=np.int64
        next_state, reward, done, info = x
        return next_state, reward, done, info

    def run(self):
        for e in range(self.EPISODES):
            state = self.reset(self.env)
            done, score, SAVING = False, 0, ''
            # Instantiate or reset games memory
            states, actions, rewards = [], [], []
            while not done:
                #self.env.render()
                # Actor picks an action
                action = self.act(state)
                # Retrieve new state, reward, and whether the state is terminal
                next_state, reward, done, _ = self.step(action, self.env, state)
                # Memorize (state, action, reward) for training
                states.append(state)
                action_onehot = np.zeros([self.action_size])
                action_onehot[action] = 1
                actions.append(action_onehot)
                rewards.append(reward)
                # Update current state
                state = next_state
                score += reward
                if done:
                    average = self.PlotModel(score, e)
                    # saving best models
                    if average >= self.max_average:
                        self.max_averagstepe = average
                        self.save()
                        SAVING = "SAVING"
                    else:
                        SAVING = ""
                    print("episode: {}/{}, score: {}, average: {:.2f} {}".format(e, self.EPISODES, score, average, SAVING))
                    print("type of replay ", type(self.replay))
                    self.replay(states, actions, rewards)
         # close environemnt when finish training
        self.env.close()

    def train(self, n_threads):
        #global exception_event
        self.env.close()
        # Instantiate one environment per thread
        envs = [gym.make(self.env_name) for i in range(n_threads)]

        # Create threads
        threads = [ threading.Thread(target=self.train_threading, daemon=False, #True,

                                     args=(self, envs[i], i)) for i in range(n_threads)]

        for t in threads:
            time.sleep(2)
            t.start()
            if A3CAgent.exception_event.is_set():
              # Retrieve the exception
              raised_exception = A3CAgent.exception_event.exception
              # Handle the exception as needed
              process_exception(A3CAgent.exception_event)
            else:
              # No exception occurred within the given timeout period
              print("No exception occurred within the timeout period")

        for t in threads:
            time.sleep(10)
            t.join()

    def train_threading(self, agent, env, thread):
      
      #global exception_event
      try:
          while self.episode < self.EPISODES:
              # Reset episode
              score, done, SAVING = 0, False, ''
              state = self.reset(env)

              # Instantiate or reset games memory
              states, actions, rewards = [], [], []
              debuggingactions = []

              #workflow and users should be in form of dict based on name and userID
              systemtime = 0 #1000
              time_slot_duration = 10#\s
              job_pointer = 0
              env.processing_q.clear()
              env.jobsetter(None)
              for v in env.vens:
                  v.clear_queue()
              simulation_duration = 400
              #avg_factor = simulation_duration/time_slot_duration
              reject_counts = 0
              update_time = 5 #seconds

              print(self.episode, "........................... episode .......................")

              for time in range(time_slot_duration, systemtime+simulation_duration): # the entire steps of the simulation
                #print("time ------- ", time)
                #updating trust value of jobs got finised during current timeslot
                if time%update_time==0:
                  while env.processing_q and env.processing_q[0][0] <= time:
                    temp = heapq.heappop(env.processing_q)
                    done_job = temp[1]
                    if done_job.assigned_to=="rejected":
                      raise Exception("job rejected and added to processing ", done_job)
                    done_job.assigned_to.job_is_done(done_job)

                #add new incoming jobs to the queue
                while env.jobs[job_pointer].submitted_at <= time:
                    env.jobsetter(env.jobs[job_pointer])

                    state = env.update_state_jq(state)
                    action = agent.act(state)
                    
                    temp = np.copy(state)
                    states.append(temp)
                    next_state, reward, done, _ = self.step(action, env, state)
                    #states.append(state)
                    action_onehot = np.zeros([self.action_size])
                    action_onehot[action] = 1
                    actions.append(action_onehot)
                    debuggingactions.append(action)
                    rewards.append(reward)
                    score += (1.0/len(env.jobs))*reward
                    state = next_state
                    # env.jobs[job_pointer].assigned_to = "rejected"
                    job_pointer += 1

              self.lock.acquire()
              self.replay(states, actions, rewards)
              self.lock.release()
              #print()
              #for i in range(len(states)):
              #  print(states[i],"\t",actions[i],"\t", debuggingactions[i])
              #print("states ", states)
              # Update episode count
              with self.lock:
                  average = self.PlotModel(score, self.episode)
                  # saving best models
                  if average >= self.max_average:
                      self.max_average = average
                      self.save()
                      SAVING = "SAVING"
                  else:
                      SAVING = ""
                  if(self.episode < self.EPISODES):
                      self.episode += 1
              #print("states ", states)
              #for state in states:
              #  print(state, self.Actor.predict(state)[0])
          with open("performance.csv", 'a') as f:
              for job in self.env.jobs:
                  f.write(str(job))
          env.close()
      except Exception as e:
          traceback.print_exception(type(e), e, e.__traceback__)
          A3CAgent.exception_event.set()
          A3CAgent.exception_event.exception = e

    def test(self, Actor_name, Critic_name, start_time, end_time):
        self.load(Actor_name, Critic_name)
        self.env.jobs = generate_jobs(self.env.workflows, self.env.users, start_time, end_time)
        systemtime = start_time
        update_time = 5
        score = 0
        state = self.reset(self.env)
        job_pointer = 0
    
        for e in range(100):
            for time in range(systemtime, systemtime+end_time):
            #updating trust value of jobs got finised during current timeslot
                if time%update_time==0:
                    while self.env.processing_q and self.env.processing_q[0][0] <= time:
                        temp = heapq.heappop(self.env.processing_q)
                        done_job = temp[1]
                        if done_job.assigned_to=="rejected":
                            raise Exception("job rejected and added to processing ", done_job)
                        done_job.assigned_to.job_is_done(done_job)
            
                while self.env.jobs[job_pointer].submitted_at <= time:
                    self.env.jobsetter(self.env.jobs[job_pointer])
                    state = self.env.update_state_jq(state)
                    self.env.render()
                    action = np.argmax(self.Actor.predict(state))
                    state, reward, done, _ = self.step(action, self.env, state)
                    score += reward
                    job_pointer += 1
        print("episode: {}/{}, score: {}".format(e, self.EPISODES, score))
        with open("performance.csv", 'a') as f:
            for job in self.env.jobs:
                f.write(str(job))

        self.env.close()

if __name__ == "__main__":'
    agent = A3CAgent()
    #agent.run() # use as A2Cthe error detail  <threading.Event object at 0x7f0a56f5ed70>
    agent.train(n_threads=2) # use as A3C
    #agent.test('Models_1000/VECEnv-RS_A3C_0.001_Actor.h5','Models_1000/VECEnv-RS_A3C_0.001_Critic.h5',start_time=0, end_time=3600)
    #agent.test('Models/Pong-v0_A3C_2.5e-05_Actor.h5', print("processing ", j.submitted_at, j.expected_exe_time, j.actual_exe_time, j.finished_at)'')