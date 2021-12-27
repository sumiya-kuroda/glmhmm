#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 14:46:44 2021

@author: irisstone

Miscellaneous helper functions for fitting and analyzing GLM/HMM code

"""

import numpy as np
import scipy.io as sio

def permute_states(M,method='self-transitions',param='transitions',order=None,ix=None):
    
    '''
    Parameters
    ----------
    M : matrix of probabilities for input parameter (transitions, observations, or initial states)
    Methods --- 
        self-transitions : permute states in order from highest to lowest self-transition value (works
             only with transition probabilities as inputs)
        order : permute states according to a given order
    param : specifies the input parameter
    order : optional, specifies the order of permuted states for method=order
    
    Returns
    -------
    M_perm : M permuted according to the specified method/order
    order : the order of the permuted states
    '''
    
    # check for valid method
    method_list = {'self-transitions','order','weight value'}
    if method not in method_list:
        raise Exception("Invalid method: {}. Must be one of {}".
            format(method, method_list))
        
    # sort according to transitions
    if method =='self-transitions':
        
        if param != 'transitions':
            raise Exception("Invalid parameter choice: self-transitions permutation method \
                            requires transition probabilities as parameter function input")
        diags = np.diagonal(M) # get diagonal values for sorting
        
        order = np.flip(np.argsort(diags))
        
        M_perm = np.zeros_like(M)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                M_perm[i,j] = M[order[i],order[j]]
                
    # sort according to given order
    if method == 'order':
        if param=='transitions':
            M_perm = np.zeros_like(M)
            for i in range(M.shape[0]):
                for j in range(M.shape[1]):
                    M_perm[i,j] = M[order[i],order[j]]
        if param=='observations':
            M_perm = np.zeros_like(M)
            for i in range(M.shape[0]):
                M_perm[i,:] = M[order[i],:]
        if param=='weights':
            M_perm = np.zeros_like(M)
            for i in range(M.shape[0]):
                M_perm[i,:,:] = M[order[i],:,:]
                
    # sort by the value of a particular weight
    if method == 'weight value':
        if ix is None:
            raise Exception("Index of weight ix must be specified for this method")
        
        order = np.flip(np.argsort(M[:,ix]))
        
        M_perm = np.zeros_like(M)
        for i in range(M.shape[0]):
            M_perm[i,:] = M[order[i],:]
    
    return M_perm, order 


def find_best_fit(lls):

    return np.argmax(np.nanmax(lls,axis=1))

def compare_top_weights(w,ixs,tol=0.05):
    '''
    compares the weights associated with the top lls from multiple glm-hmm fits and checks if each 
    weight matches within the given tolerance
    '''
    
    best_weights = w[ixs[0],:,:]
    diff = np.zeros((len(ixs),w.shape[1],w.shape[2]))
    for i in range(1,len(ixs)): # for each specified fit (associated with the top lls)
        for j in range(w.shape[1]): # for each state
            diff[i-1,j,:] = abs(best_weights[j,:] - w[ixs[i],j,:])
            
    if np.any(diff > tol):
        print('One or more weights differ by more than the set tolerance. The largest difference was %.2f.' %(np.max(diff)))
        print('Try changing the tolerance or decreasing the number of top fits to compare.')
    else:
        print('None of the weights differ by more than the set tolerance. The largest difference was %.2f.' %(np.max(diff)))
        print('This confirms that the top fits (as specified) all converged on the same solution.')

def convert_ll_bits(LL,L0,nT):
    '''
    Description: converts regular loglikelihood values into "bits."
    Inputs: 
        LL: loglikelihood values (1xn vector)
        L0 = base loglikelihood for subtraction (e.g. LL of bias only) (scalar)
        nT = length of data (scalar)
    Outputs: loglikelihood in "bits" (1xn vector)
    '''

    LL_bits = (LL - L0) / (nT * np.log(2))
            
    return LL_bits

def reshape_obs(y):

    # reshape y from vector of indices to one-hot encoded array for matrix operations in neglogli
    if len(y.shape) == 1:
        yint = y.astype(int)
        y = np.zeros((yint.shape[0], yint.max()+1))
        y[np.arange(yint.shape[0]),yint] = 1

    return y

def convertContraIpsi(laserStatus,cues,choices,dates,save_path,scale=1):
    
    cues = cues*scale
    OFF_data, ONLEFT_data, ONRIGHT_data, OFF_data_right, OFF_data_left = [],[],[],[],[]

    choices = 1-choices # flip all choices
    for i in range(len(choices)):
        if np.round(laserStatus[i],2) == 0: #if laser is off
            OFF_data.append([cues[i],choices[i]])
            if dates[i] == 1: # if date is even
                OFF_data_right.append([cues[i]*-1,1-choices[i]])
            elif dates[i] == -1: # if date is odd
                OFF_data_left.append([cues[i],choices[i]])
        if np.round(laserStatus[i],2) == -1: #if laser is on LEFT
            ONLEFT_data.append([cues[i],choices[i]])
        if np.round(laserStatus[i],2) == 1: #if laser is on RIGHT
            ONRIGHT_data.append([cues[i],choices[i]])

    # IPSI/CONTRA LASER DATA
    ONRIGHT_flipped = []
    for i in range(len(ONRIGHT_data)):
        diffT_flipped = ONRIGHT_data[i][0] * -1
        ONRIGHT_flipped.append([diffT_flipped,1-ONRIGHT_data[i][1]])

    ON_data = ONLEFT_data + ONRIGHT_flipped
    OFF_data = OFF_data_left + OFF_data_right 

    OFF_data = np.array(OFF_data)
    ONLEFT_data = np.array(ONLEFT_data)
    ONRIGHT_data = np.array(ONRIGHT_data)
    ON_data = np.array(ON_data)
    

    D = {'diffT_laserOFF': OFF_data[:,0],
     'choices_laserOFF': OFF_data[:,1],
     'diffT_laserON': ON_data[:,0],
     'choices_laserON': ON_data[:,1]}
    sio.savemat(save_path,D)

    return D

def uniqueSessionIDs(sessions):

    '''
    Creates unique ID for each session (number of unique IDs == number of unique sessions)

    Parameters
    ----------
    sessions: vector containing the starting indices of each session
    
    Returns
    -------
    uniqueSessionIDs: vector of length N assigning each trial a unique session ID 

    '''

    N = sessions[-1] # total number of trials
    uniqueSessionIDs = np.zeros(N)
    sessionID = 0
    count = 1
    for i in range(N):
        if i < sessions[count]: # for trials corresponding to length of each session
            uniqueSessionIDs[i] = sessionID # assign session ID to all trials in the same session
        else: 
            count += 1 # move to next session
            sessionID += 1 # add new session ID
            uniqueSessionIDs[i] = sessionID 

    return uniqueSessionIDs

def splitData(sessions,mouseIDs,testSize=0.2,seed=0):

    '''
    Splits data into train and test sets for cross validation by partitioning entire sessions and balancing 
    the number of animals in each test set. 

    Parameters
    ----------
    sessions : vector containing the starting indices of each session
    mouseIDs : vector of length N indicating which animal each trial is associated with
    testSize : the percentage of sessions to put in each test set
    seed : random seed determines how train and test sets are split
    
    Returns
    -------
    trainTrialIxs: vector with indices from all data associated with training set
    trainSessionStartIxs: vector contaiining the starting indices of each session in the training set
    testTrialIxs: indices from all data associated with test set 
    testSessionStartIxs: vector contaiining the starting indices of each session in the test set


    '''

    sessionIDs = uniqueSessionIDs(sessions)
    sessionLabels = np.unique(sessionIDs) # unique session labels (one for each unique session)
    numSessions = len(sessionLabels) # number of unique sessions
    testLength = round(numSessions * testSize) # number of sessions to set aside for test data
        
    # make sure equal number of sessions are taken from each mouse
    unique_mouseID = np.unique(mouseIDs) # IDs of each mouse
    numTestSessions = round(testLength/len(unique_mouseID)) # number of sessions to take from each mouse for test set
    np.random.seed(seed)

    testSessions = []
    for i in range(len(unique_mouseID)):
        mouseSessions = np.unique(sessionIDs[mouseIDs==unique_mouseID[i]]) # find session numbers associated with each mouse
        try: selectedSessions = np.sort(np.random.choice(mouseSessions,size=numTestSessions,replace=False)) # randomly select sessions for test set
        except ValueError: selectedSessions = np.sort(mouseSessions) # if too few sessions available, take all of them
    
        testSessions.append(selectedSessions)

    testSessionLabels = np.sort(np.array([item for sublist in testSessions for item in sublist]).astype(int))
    trainSessionLabels = np.delete(sessionLabels,testSessionLabels).astype(int) 

    # get session lengths associated with test and train sets
    testSessionIxs = sessions[testSessionLabels]
    testSessionLengths = np.diff(sessions)[testSessionLabels]
    trainSessionIxs = sessions[trainSessionLabels]
    trainSessionLengths = np.diff(sessions)[trainSessionLabels]

    # get all the indices of the data points for the test set
    testTrialIxs = np.zeros(np.sum(testSessionLengths), dtype=int)
    testSessionStartIxs = np.zeros(len(testSessionIxs)+1, dtype=int)
    count = 0
    for i in range(len(testSessionIxs)):
    	testSessionStartIxs[i] = count
    	sessLength = testSessionLengths[i]
    	testTrialIxs[count:count+sessLength] = np.arange(testSessionIxs[i],testSessionIxs[i]+sessLength,1)
    	count = count+sessLength
    testSessionStartIxs[-1] = count

    # get all the indices of the data points for the test set
    trainTrialIxs = np.zeros(np.sum(trainSessionLengths), dtype=int)
    trainSessionStartIxs = np.zeros(len(trainSessionIxs)+1, dtype=int)
    count = 0
    for i in range(len(trainSessionIxs)):
    	trainSessionStartIxs[i] = count
    	sessLength = trainSessionLengths[i]
    	trainTrialIxs[count:count+sessLength] = np.arange(trainSessionIxs[i],trainSessionIxs[i]+sessLength,1)
    	count = count+sessLength
    trainSessionStartIxs[-1] = count

    return trainTrialIxs, trainSessionStartIxs, testTrialIxs, testSessionStartIxs



