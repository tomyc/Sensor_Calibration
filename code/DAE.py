import scipy.io as sio
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import tensorflow as tf
import tensorflow.contrib.slim as slim

def run(ratio):
	data_dir = './Data'
	noisy_data_1 = np.load('ch1_data.npy')[:,:,0] #noisy signal, totally off
	noisy_data_2 = np.load('ch2_data.npy')[:,:,0] #noisy signal
	#noisy_data = np.concatenate([noisy_data_1[:330], noisy_data_2[330:]], 0)
	noisy_data = noisy_data_2
	good_data = np.load('ch3_data.npy')[:,:,0] #good signal
	input_data = []
	output_data = []
	max_val = []
	min_val = []
	for i, data_i in enumerate(noisy_data):
		# normalize with training data
		max_val += [np.max(data_i)]
		min_val += [np.min(data_i)]
		input_data += [(data_i-np.min(data_i))/(np.max(data_i)-np.min(data_i))]
		output_data += [(good_data[i]-np.min(data_i))/(np.max(data_i)-np.min(data_i))]
	if 0:
		test_input = []
		test_output = []
		train_input = []
		train_output = []
		train_min = []
		train_max = []
		test_min = []
		test_max = []
		for i in range(len(input_data)):
			if i%5:
				train_input += [input_data[i]]
				train_output += [output_data[i]]
				train_min += [min_val[i]]
				train_max += [max_val[i]]
			else:
				test_input += [input_data[i]]
				test_output += [output_data[i]]
				test_min += [min_val[i]]
				test_max += [max_val[i]]
		test_input = np.asarray(test_input)
		test_output = np.asarray(test_output)
		train_input = np.asarray(train_input)
		train_output = np.asarray(train_output)
		test_min = np.asarray(test_min)
		test_max = np.asarray(test_max)
		train_min = np.asarray(train_min)
		train_max = np.asarray(train_max)
	else:
		dataset_size = len(output_data)
		training_size = int(ratio*dataset_size)
		print('training data amount: {}, ratio: {}'.format(training_size, ratio))
		idx = np.arange(dataset_size)
		np.random.shuffle(idx)
		output_data = np.asarray(output_data)
		input_data = np.asarray(input_data)
		min_val = np.asarray(min_val)
		max_val = np.asarray(max_val)
		train_output = output_data[idx[:training_size]]
		test_output = output_data[idx[training_size:]]
		train_input = input_data[idx[:training_size]]
		test_input = input_data[idx[training_size:]]
		train_min = min_val[idx[:training_size]]
		train_max = max_val[idx[:training_size]]
		test_min = min_val[idx[training_size:]]
		test_max = max_val[idx[training_size:]]



	batch_size = 16
	num_time_steps = 3000
	dim_out = 1
	input_pl = tf.placeholder(tf.float32, [batch_size, num_time_steps])
	output_pl = tf.placeholder(tf.float32, [batch_size, num_time_steps])
	net = {}
	net['enc1'] = slim.fully_connected(input_pl, 1024, scope='enc/fc1')
	net['enc2'] = slim.fully_connected(net['enc1'], 1024, scope='enc/fc2')
	net['enc3'] = slim.fully_connected(net['enc2'], 512, scope='enc/fc3')
	net['enc4'] = slim.fully_connected(net['enc3'], 512, scope='enc/fc4')
	net['enc5'] = slim.fully_connected(net['enc4'], 256, scope='enc/fc5')
	net['enc6'] = slim.fully_connected(net['enc5'], 256, scope='enc/fc6')
	net['dec1'] = slim.fully_connected(net['enc6'], 512, scope='dec/fc1')
	net['dec2'] = slim.fully_connected(net['dec1'], 512, scope='dec/fc2')
	net['dec3'] = slim.fully_connected(net['dec2'], 1024, scope='dec/fc3')
	net['dec4'] = slim.fully_connected(net['dec3'], 1024, scope='dec/fc4')
	net['dec5'] = slim.fully_connected(net['dec4'], 3000, scope='dec/fc5')
	net['dec6'] = slim.fully_connected(net['dec5'], 3000, activation_fn=tf.identity, scope='dec/fc6')
	net['residual'] = net['dec6']
	net['denoised'] = net['residual'] #+ input_pl
	loss_l2 = tf.reduce_mean(tf.abs(net['denoised'] - output_pl))
	loss_l1 = tf.reduce_max(tf.abs(net['denoised'] - output_pl))
	loss = loss_l2 + loss_l1 #max error regularizer

	## OPTIMIZER ## note: both optimizer and learning rate is not found in the paper
	optimizer = tf.train.AdamOptimizer(1e-5, beta1=0.5)
	grads = optimizer.compute_gradients(loss, tf.all_variables())
	train_op = optimizer.apply_gradients(grads)

	## training starts ###
	FLAGS = tf.app.flags.FLAGS
	tfconfig = tf.ConfigProto(
		allow_soft_placement=True,
		log_device_placement=True,
	)
	tfconfig.gpu_options.allow_growth = True
	sess = tf.Session(config=tfconfig)
	init = tf.global_variables_initializer()
	sess.run(init)


	max_epoch = 2000
	train_loss_l1_val_hist = []
	test_loss_l1_val_hist = []
	train_loss_l2_val_hist = []
	test_loss_l2_val_hist = []
	print(train_input.shape, test_input.shape)
	for eq_i in range(max_epoch):
		# training data, for optimization
		num_itr = train_input.shape[0] / batch_size
		ave_loss_l1_val_train = []
		ave_loss_l2_val_train = []
		for i in range(num_itr):
			feed_dict_train = {input_pl: train_input[i*batch_size:(i+1)*batch_size],
						 output_pl: train_output[i*batch_size:(i+1)*batch_size]}
			loss_l2_val, loss_l1_val, _ = sess.run([loss_l2, loss_l1, train_op], feed_dict_train)
			ave_loss_l1_val_train += [loss_l1_val]
			ave_loss_l2_val_train += [loss_l2_val]
		train_loss_l1_val_hist += [np.mean(ave_loss_l1_val_train)]
		train_loss_l2_val_hist += [np.mean(ave_loss_l2_val_train)]
		# testing data
		ave_loss_l1_val_test = []
		ave_loss_l2_val_test = []
		num_itr = test_input.shape[0] / batch_size
		for i in range(num_itr):
			feed_dict_test = {input_pl: test_input[i*batch_size:(i+1)*batch_size],
						 output_pl: test_output[i*batch_size:(i+1)*batch_size]}
			loss_l2_val, loss_l1_val = sess.run([loss_l2, loss_l1], feed_dict_test)
			ave_loss_l2_val_test += [loss_l2_val]
			ave_loss_l1_val_test += [loss_l1_val]
		test_loss_l1_val_hist += [np.mean(ave_loss_l1_val_test)]
		test_loss_l2_val_hist += [np.mean(ave_loss_l2_val_test)]

		print(eq_i, np.mean(ave_loss_l1_val_train), np.mean(ave_loss_l1_val_test), np.mean(ave_loss_l2_val_train), np.mean(ave_loss_l2_val_test))

	plt.figure()
	plt.subplot(2,1,1)
	plt.plot(train_loss_l2_val_hist[3:], label='training l2 loss')
	plt.plot(test_loss_l2_val_hist[3:], label='testing l2 loss')
	plt.legend()
	plt.subplot(2,1,2)
	plt.plot(train_loss_l1_val_hist[3:], label='training l1 loss')
	plt.plot(test_loss_l1_val_hist[3:], label='testing l1 loss')
	plt.legend()
	plt.show()

	#plt.plot(sess.run(net['output'], feed_dict_train)[idx], label='true')
	i = 0
	input_data_val = test_input[i*batch_size:(i+1)*batch_size]
	residual_data_val = sess.run(net['residual'], {input_pl: input_data_val})
	denoised_data_val = sess.run(net['denoised'], {input_pl: input_data_val})
	reference_data_val = test_output[i*batch_size:(i+1)*batch_size]

	if 1:
		test_max_val = np.expand_dims(test_max[i*batch_size:(i+1)*batch_size], 1)
		test_min_val = np.expand_dims(test_min[i*batch_size:(i+1)*batch_size], 1)
		input_data_val = (input_data_val) * (test_max_val - test_min_val)  + test_min_val
		residual_data_val = (residual_data_val) * (test_max_val - test_min_val)  + test_min_val
		denoised_data_val = (denoised_data_val) * (test_max_val - test_min_val)  + test_min_val
		reference_data_val = (reference_data_val) * (test_max_val - test_min_val)  + test_min_val

	np.save('input_data_val_ch2.npy', input_data_val)
	np.save('output_data_val_ch2.npy', reference_data_val)
	np.save('denoised_data_val_ch2.npy', denoised_data_val)

	for idx in range(5):
		plt.figure(figsize=(7,15))
		plt.subplot(5,1,1)
		plt.plot(input_data_val[idx],label='bad sensor')
		plt.legend()
		plt.subplot(5,1,2)
		plt.plot(residual_data_val[idx], label='residual sensor')
		plt.legend()
		plt.subplot(5,1,3)
		plt.plot(denoised_data_val[idx], label='denoised signal')
		plt.legend()
		plt.subplot(5,1,4)
		plt.plot(reference_data_val[idx], label='good sensor')
		plt.legend()
		plt.subplot(5,1,5)
		plt.plot(reference_data_val[idx]-denoised_data_val[idx], label='error')
		plt.legend()
	plt.show()

if __name__ == '__main__':
	# for ratio in range(0.,1,10):
	run(0.5)


