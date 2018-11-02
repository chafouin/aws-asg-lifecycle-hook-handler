# -*- coding: utf-8 -*-

import unittest

import boto3
import requests_mock
from moto import mock_autoscaling
from moto import mock_ec2

import lifecycle_hook_handler


@mock_autoscaling
@mock_ec2
class LifecyleHookHandlerTest(unittest.TestCase):
    def setUp(self):
        self.instance_id = 'i-08d283b262365ba87'
        self.aws_metadata_endpoint = 'http://169.254.169.254/latest/meta-data/instance-id'

    # TODO: create dummy autoscaling group to tests
    #    autoscaling = boto3.client('autoscaling')
    #    autoscaling.create_auto_scaling_group(AutoScalingGroupName="moto_autoscaling_test")

    @requests_mock.Mocker()
    def test_get_instance_id(self, requests_mock):
        requests_mock.register_uri('GET', self.aws_metadata_endpoint, text=self.instance_id)
        self.assertEqual(lifecycle_hook_handler.get_instance_id(), self.instance_id)

    @requests_mock.Mocker()
    def test_get_instance_id_error(self, requests_mock):
        requests_mock.register_uri('GET', self.aws_metadata_endpoint, status_code=500)
        self.assertEqual(lifecycle_hook_handler.get_instance_id(), None)

    # Lifecycle hooks not yet supported by Moto
    #def test_get_instance_lifecycle_hook_state(self):
    #    client = boto3.client('autoscaling')
    #    client.create_launch_configuration(LaunchConfigurationName='launch_configuration_test')
    #    client.create_auto_scaling_group(AutoScalingGroupName="autoscaling_test", MinSize=0, MaxSize=1,
    #                                     LaunchConfigurationName='launch_configuration_test')
    #    client.put_lifecycle_hook(LifecycleHookName='lifecycle_hook_test',
    #                              AutoScalingGroupName='launch_configuration_test')
    #    print(client.describe_auto_scaling_groups())
    #    lifecycle_hook_handler.get_instance_lifecycle_hook_state()
