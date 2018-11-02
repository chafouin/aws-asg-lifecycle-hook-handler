#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Script that checks the lifecycle state of the current instance & run a given command if a hook is active.
Required on run on an AWS instance attached to an AutoScaling Group.


Execution flow :
 1. Get instance ID
 2. Get instance's lifecycle state
 3. If state is "Terminating:Wait" continue else stop
 4. Run a defined command
"""

import boto3
import botocore
import requests

import argparse
import datetime
import logging
import subprocess
import time

_AUTOSCALING = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _get_autoscaling(region='eu-west-1'):
    """
    Get the global variable containing the boto3 autoscaling group client. Useful between multiple AWS boto3
    invocation, the client will cached, so the initialization time reduced and the performance improved.

    :return: boto3 autoscaling client
    """
    global _AUTOSCALING
    if _AUTOSCALING is None:
        _AUTOSCALING = boto3.client('autoscaling', region_name=region)
    return _AUTOSCALING


def get_args():
    """
    This function parses and return arguments passed to the script.

    :return: (dict) configuration
    """
    config = {
        'region': '',
        'command': '',
        'instance_id': '',
        'autoscaling_group_name': '',
        'lifecycle_hook': '',
        'action_result': '',
        'heartbeat_rate': 0,
        'timeout': 0,
        'debug': False
    }

    parser = argparse.ArgumentParser(
        description='Script to execute given command when receiving a AutoScaling lifecycle hook')

    parser.add_argument(
        '-r', '--region', type=str, help='AWS region', required=False, default="eu-west-1")
    parser.add_argument(
        '-c', '--command', type=str, help='Command to run', required=True)
    parser.add_argument(
        '-l', '--lifecyclehook', type=str, help='Lifecycle hook name', required=False)
    parser.add_argument(
        '-g', '--autoscalinggroup', type=str, help='Autoscaling group name', required=False)
    parser.add_argument(
        '-a', '--actionresult', type=str, help='Lifecycle hook result: ABANDON or CONTINUE', default="CONTINUE")
    parser.add_argument(
        '-b', '--heartbeat', type=float, help='Heartbeat rate in seconds', required=False, default=10)
    parser.add_argument(
        '-t', '--timeout', type=float, help='Timeout in seconds', required=False, default=300)
    parser.add_argument(
        '-d', '--debug', help='Debug mode', required=False, action='store_true', default=False)

    args = parser.parse_args()

    if args.region is not None:
        config['region'] = args.region
    if args.command is not None:
        config['command'] = args.command
    if args.lifecyclehook is not None:
        config['lifecycle_hook'] = args.lifecyclehook
    if args.autoscalinggroup is not None:
        config['autoscaling_group_name'] = args.autoscalinggroup
    if args.actionresult is not None:
        config['action_result'] = args.actionresult
    if args.heartbeat is not None:
        config['heartbeat_rate'] = args.heartbeat
    if args.timeout is not None:
        config['timeout'] = args.timeout
    if args.debug is not None:
        config['debug'] = args.debug

    config['instance_id'] = get_instance_id()

    if config['autoscaling_group_name'] == '':
        config['autoscaling_group_name'] = get_autoscaling_group_name(config['instance_id'],
                                                                      config['region'])
    if config['lifecycle_hook'] == '':
        config['lifecycle_hook']= get_lifecycle_hook_name(config['autoscaling_group_name'],
                                                          config['region'])

    return config


def get_instance_id():
    aws_metadata_endpoint = 'http://169.254.169.254/latest/meta-data/instance-id'
    logger.info("Get instance_id using AWS metadata endpoint")
    logger.debug("Send query to {0}".format(aws_metadata_endpoint))
    response = requests.get(aws_metadata_endpoint)
    if response.status_code == 200:
        logger.debug("AWS metadata endpoint response: {0}".format(response))
        return response.text
    logger.error("Get error code {0} while getting instance_id".format(response.status_code))
    return None


def get_autoscaling_group_name(instance_id, region):
    logger.info("Get autoscaling group name")
    try:
        for instance in _get_autoscaling(region).describe_auto_scaling_instances(
                InstanceIds=[instance_id])['AutoScalingInstances']:
            if instance['InstanceId'] == instance_id:
                return instance['AutoScalingGroupName']
    except botocore.exceptions.ClientError:
        logger.error("Boto raised an error while getting autoscaling group name", exc_info=True)
        raise


def get_lifecycle_hook_name(autoscaling_group_name, region):
    logger.info("Get lifecycle name attach to {0}".format(autoscaling_group_name))
    list_lifecycle_hook = _get_autoscaling(region).describe_lifecycle_hooks(AutoScalingGroupName=autoscaling_group_name)['LifecycleHooks']
    if len(list_lifecycle_hook) > 0:
        return list_lifecycle_hook[0]['LifecycleHookName']
    return None


def get_instance_lifecycle_hook_state(instance_id, region):
    logger.info("Get instance lifecycle hook status")
    try:
        for instance in _get_autoscaling(region).describe_auto_scaling_instances(
                InstanceIds=[instance_id])['AutoScalingInstances']:
            if instance['InstanceId'] == instance_id:
                return instance['LifecycleState']
    except botocore.exceptions.ClientError:
        logger.error("Boto raised an error while getting instance lifecycle hook status", exc_info=True)
        raise


def run_cmd(command, region, lifecyclehook_name, autoscaling_group_name, instance_id, heartbeat_rate, timeout):
    process = subprocess.Popen(command, shell=True)

    wait_until = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

    while True:
        return_code = process.poll()
        if return_code is not None:
            return return_code
        if wait_until < datetime.datetime.now():
            logger.info("Timing out")
            process.kill()
            return 0

        time.sleep(heartbeat_rate)
        send_heartbeat(region, lifecyclehook_name, autoscaling_group_name, instance_id)


def send_heartbeat(region, lifecyclehook_name, autoscaling_group_name, instance_id):
    _get_autoscaling(region).record_lifecycle_action_heartbeat(LifecycleHookName=lifecyclehook_name,
                                                               AutoScalingGroupName=autoscaling_group_name,
                                                               InstanceId=instance_id)
    logger.info('Heartbeat sent')


def complete_lifecycle(region, lifecyclehook_name, autoscaling_group_name, instance_id, action_result):
    _get_autoscaling(region).complete_lifecycle_action(LifecycleHookName=lifecyclehook_name,
                                                       AutoScalingGroupName=autoscaling_group_name,
                                                       InstanceId=instance_id,
                                                       LifecycleActionResult=action_result)


def check_lifecycle_state(command, region, lifecyclehook_name, autoscaling_group_name, instance_id, action_result,
                          heartbeat_rate, timeout):
    state = get_instance_lifecycle_hook_state(instance_id, region)
    logger.info("Hook state is {0}".format(state))
    if state == "Terminating:Wait":
        logger.info("Run command '{0}' before stopping instance".format(command))
        return_code = run_cmd(command,
                              region,
                              lifecyclehook_name,
                              autoscaling_group_name,
                              instance_id,
                              heartbeat_rate,
                              timeout)
        logger.info("Command returned {0}".format(return_code))
        complete_lifecycle(region,
                           lifecyclehook_name,
                           autoscaling_group_name,
                           instance_id,
                           action_result)
        logger.info("Lifecycle hook proceed request sent")
    else:
        logger.info("Nothing to do")


def main():
    config = get_args()
    if config['debug']:
        logger.setLevel(level=logging.DEBUG)
    logger.info("started")
    logger.debug("Configuration loaded: {0}".format(config))
    if not config['instance_id']:
        raise RuntimeError("Could not get the instance id. Maybe the script is not run on an EC2 instance or the "
                           "metadata endnpoint is unreachable.")
    check_lifecycle_state(config['command'],
                          config['region'],
                          config['lifecycle_hook'],
                          config['autoscaling_group_name'],
                          config['instance_id'],
                          config['action_result'],
                          config['heartbeat_rate'],
                          config['timeout'])
    logger.info("AWS AutoScaling lifecycle hook handler script executed successfully")


if __name__ == "__main__":
    main()
