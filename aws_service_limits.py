#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto.ec2.autoscale
import boto.ec2.elb
import boto.ec2.cloudwatch
import boto.rds2

import blackbird.plugins.base


class ConcreteJob(blackbird.plugins.base.JobBase):

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options, queue, logger)
        # boto.ec2.EC2Connection object
        self.conn = None
        self._resources = [
            'autoscale',
            'ec2',
            'elb',
            'rds'
        ]
        self._limits = [
            'autoscale',
            'ec2'
        ]

    def _enqueue(self, item):
        pass

    def _fetch_service_limit(self, limits=None):
        """
        Fetch AWS service limits
        :rtype: dict
        :return: AWS Service limits
        """
        result = dict()
        if limits is None:
            limits = self._limits
        for entry in limits:
            result.update(getattr(
                self,
                '_fetch_limit_{0}'.format(entry)
            ))

        return result

    def _fetch_limit_autoscale(self):
        """
        Fetch AWS AutoScaling limits
        1. Max AutoScaling groups
        2. Max launch configurations
        :rtype: dict
        :return: AutoScaling limits
        """
        conn = boto.ec2.autoscale.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        account_limits = conn.get_account_limits()
        return {
            'ec2.max_autoscaling_grouos':
            account_limits.max_autoscaling_groups,
            'ec2.max_launch_configurations':
            account_limits.max_launch_configurations
        }

    def _fetch_limit_ec2(self):
        """
        Fetch EC2 limits
        1. Max elastic IPs
        2. Max instances
        :return:
        """
        result = dict()
        conn = boto.ec2.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        max_instances = conn.describe_account_attributes(
            attribute_names=['max-instances']
        )[0]
        if len(max_instances.attribute_values) > 1:
            self.logger.warn(
                (
                    '"max-instances" account attribute object has '
                    'values more than one.'
                )
            )
        else:
            result['ec2.max-instances'] = max_instances.attribute_values[0]

        platform = conn.describe_account_attributes(
            attribute_names=['supported-platforms']
        )[0]
        if platform.attribute_values[0] != 'VPC':
            max_elastic_ips = conn.describe_account_attributes(
                attribute_names='max-elastic-ips'
            )[0].attribute_values[0]
        else:
            max_elastic_ips = conn.describe_account_attributes(
                attribute_names='voc-max-elastic-ips'
            )[0].attribute_values[0]
        result['ec2.supported_platforms'] = platform.attribute_values[0]

        result['ec2.max_elastic_ips'] = max_elastic_ips

        return result

    def _fetch_using_resources(self, resources=None):
        """
        Fetch using AWS Resources by self._fetch_using_XXXXX_resources
        :rtype: dict
        :return: Specified using aws resources
        """
        if resources is None:
            resources = self._resources
        result = dict()

        for entry in resources:
            result.update(getattr(
                self,
                '_fetch_using_{0}_resources'.format(entry)
            ))

        return result

    def _fetch_using_autoscale_resources(self):
        """
        Fetch using resources of AWS AutoScale.
        1. launch configurations
        2. autoscaling groups
        :rtype: dict
        :return: using resources of AWS AutoScale.
        """
        conn = boto.ec2.autoscale.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        return {
            'autoscale.launch_configurations':
            len(conn.get_all_launch_config()),
            'autoscale.groups':
            len(conn.get_all_groups()),
        }

    def _fetch_using_ec2_resources(self):
        """
        Fetch using resources of AWS EC2.
        1. using Elastic IP addresses
        2. running on-demand instances
        :rtype: dict
        :return: using resources of AWS EC2.
        """
        state_code_running = 16
        conn = boto.ec2.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        return {
            'ec2.elastic_ip_addresses':
            len(conn.get_all_addresses()),
            'ec2.running_instances':
            len(conn.get_all_instances(
                filters={
                    'instance-state-code': state_code_running
                }
            ))
        }

    def _fetch_using_elb_resources(self):
        """
        Fetch using resources of Elastic Load Balancing.
        1. number of ELBs
        :return: dict
        :return: using resources of Elastic Load Balancing.
        """
        conn = boto.ec2.elb.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        return {
            'elb.load_balancers':
            conn.get_all_load_balancers()
        }

    def _fetch_using_rds_resources(self):
        """
        Fetch using resources of Amazon RDS.
        1. number of instances
        2. total storage for all DB instances (Giga Bytes)
        3. read replicas per master
        :rtype: dict
        :return: using resources of Amazon RDS.
        """
        conn = boto.rds2.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get(
                'aws_access_key_id'
            ),
            aws_secret_access_key=self.options.get(
                'aws_secret_access_key'
            )
        )
        db_instances = conn.describe_db_instances().get(
            'DescribeDBInstancesResponse'
        ).get(
            'DescribeDBInstancesResult'
        ).get(
            'DBInstances'
        )

        total_storage = 0
        for entry in db_instances:
            allocated_storage = entry.get('AllocatedStorage')
            if allocated_storage is None:
                raise blackbird.plugins.base.BlackbirdPluginError(
                    'Could not get "Allocated Storage" of rds instance.'
                )
            total_storage += int(allocated_storage)

        max_read_replicas_per_master = 0
        for entry in db_instances:
            number_of_replicas = entry['ReadReplicaDBInstanceIdentifiers']
            if max_read_replicas_per_master < number_of_replicas:
                max_read_replicas_per_master = number_of_replicas

        return {
            'rds.instances':
            len(db_instances),
            'rds.total_storage':
            total_storage,
            'rds.read_replicas_per_master':
            max_read_replicas_per_master
        }


    def build_items(self):
        pass


class Validator(blackbird.plugins.base.ValidatorBase):
    """
    Validate configuration object.
    """
    # :TODO 10/21 tasks
    pass


class AWSResourceUsedItem(blackbird.plugins.base.ItemBase):
    """
    Enqueued item object.
    """

    def __init__(self, key, value, host):
        super(AWSResourceUsedItem).__init__(key, value, host)

        self.__data = dict()
        self._generate()

    @property
    def data(self):
        """
        :rtype: dict
        :return: AWSResourceItem.__data
        """
        return self.__data

    def _generate(self):
        self.__data['key'] = 'aws_resource.used.{0}'.format(self.key)
        self.__data['value'] = self.value
        self.__data['host'] = self.host
        self.__data['clock'] = self.clock


class AWSResourceLimitItem(blackbird.plugins.base.ItemBase):
    """
    Enqueued item object.
    """

    def __init__(self, key, value, host):
        super(AWSResourceLimitItem).__init__(key, value, host)

        self.__data = dict()
        self._generate()

    @property
    def data(self):
        """
        :rtype: dict
        :return: AWSResourceItem.__data
        """
        return self.__data

    def _generate(self):
        self.__data['key'] = 'aws_resource.limit.{0}'.format(self.key)
        self.__data['value'] = self.value
        self.__data['host'] = self.host
        self.__data['clock'] = self.clock

