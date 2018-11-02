# AWS AutoScaling lifecycle hook handler

This script can be use to react on an Autoscaling group lifecycle hook, it is useful if you need to stop the instance
processing before teminating it, in a graceful manner. See [AWS documentation](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)
for more information on lifecycle hook. When the termination hook is pending, the autoscaling group will wait a
certain amount of time for a signal to release the hook and terminate the instance. The script will check the hook and
if it is pending, it will run the given command and wait for it to finish. During the execution time, it will
periodically send an heartbeat signal to avoid the hook to time out. After the command execution, the script will
release the hook and the instance will be terminated by the ASG.

## Requirements

* Python 3.4+
* Pipenv

## Usage

```
$ ./lifecycle_hook_handler.py -h
usage: lifecycle_hook_handler.py [-h] [-r REGION] -c COMMAND -l LIFECYCLEHOOK
                                 -g AUTOSCALINGGROUP [-a ACTIONRESULT]
                                 [-b HEARTBEAT] [-d]

Script to execute given command when receiving a AutoScaling lifecycle hook

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        AWS region
  -c COMMAND, --command COMMAND
                        Command to run
  -l LIFECYCLEHOOK, --lifecyclehook LIFECYCLEHOOK
                        Lifecycle hook name
  -g AUTOSCALINGGROUP, --autoscalinggroup AUTOSCALINGGROUP
                        Autoscaling group name
  -a ACTIONRESULT, --actionresult ACTIONRESULT
                        Lifecycle hook result: ABANDON or CONTINUE
  -b HEARTBEAT, --heartbeat HEARTBEAT
                        Heartbeat rate in seconds
  -d, --debug           Debug mode
```

## License

[GNUv3 Licence](https://www.gnu.org/licenses/gpl-3.0.txt)
