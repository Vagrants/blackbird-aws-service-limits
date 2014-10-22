#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto.ec2.autoscale
import boto.ec2.elb
import boto.ec2.cloudwatch
import boto.dynamodb2
import boto.rds2

import blackbird.plugins.base


class ConcreteJob(blackbird.plugins.base.JobBase):

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options, queue, logger)
        # boto.ec2.EC2Connection object
        self.conn = None
        self._resources = [
            'autoscale',
            'dynamodb',
            'ec2',
            'elb',
            'rds'
        ]
        self._limits = [
            'autoscale',
            'ec2'
        ]

    def _enqueue(self, item):
        self.queue.put(item, block=False)
        self.logger.debug(
            'Inserted to queue {key}:{value}'
            ''.format(
                key=item.key,
                value=item.value
            )
        )

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
            )())

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
            'autoscale.max_groups':
            account_limits.max_autoscaling_groups,
            'autoscale.max_launch_configurations':
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
            result['ec2.max_instances'] = max_instances.attribute_values[0]

        platform = conn.describe_account_attributes(
            attribute_names=['supported-platforms']
        )[0]
        if platform.attribute_values[0] != 'VPC':
            max_elastic_ips = conn.describe_account_attributes(
                attribute_names='max-elastic-ips'
            )[0].attribute_values[0]
        else:
            max_elastic_ips = conn.describe_account_attributes(
                attribute_names='vpc-max-elastic-ips'
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
            )())

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
            len(conn.get_all_launch_configurations()),
            'autoscale.groups':
            len(conn.get_all_groups()),
        }

    def _fetch_using_dynamodb_resources(self):
        """
        Fetch using resources of DynamoDB.
        1. Read capacity units (individual table)
        2. Write capacity units (individual table)
        3. Read capacity units (account)
        4. Write capacity units (account)
        :rtype: dict
        :return: Current write or read capacity units
        """
        conn = boto.dynamodb2.connect_to_region(
            self.options.get('region_name'),
            aws_access_key_id=self.options.get('aws_access_key_id'),
            aws_secret_access_key=self.options.get('aws_secret_access_key')
        )
        table_list = conn.list_tables().get('TableNames')
        if table_list is None:
            raise blackbird.plugins.base.BlackbirdPluginError(
                'No "TableNames" key. Is returned object structure changed?'
            )

        read_capacity_units_individual_table = 0
        write_capacity_units_individual_table = 0
        read_capacity_units_per_account = 0
        write_capacity_units_per_account = 0
        for entry in table_list:
            table = conn.describe_table(table_name=entry)
            provisioned_through_put = table['Table']['ProvisionedThroughput']

            read_capacity_units = (
                provisioned_through_put['ReadCapacityUnits']
            )
            write_capacity_units = (
                provisioned_through_put['WriteCapacityUnits']
            )
            read_capacity_units_per_account += read_capacity_units
            write_capacity_units_per_account += write_capacity_units

            if read_capacity_units_individual_table < read_capacity_units:
                read_capacity_units_individual_table = read_capacity_units
            if write_capacity_units_individual_table < write_capacity_units:
                write_capacity_units_individual_table = write_capacity_units

        return {
            'dynamodb.read_capacity_units_individual_table':
            read_capacity_units_individual_table,
            'dynamodb.write_capacity_units_individual_table':
            write_capacity_units_individual_table,
            'dynamodb.read_capacity_units_per_account':
            read_capacity_units_per_account,
            'dynamodb.write_capacity_units_per_account':
            write_capacity_units_per_account
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
            'ec2.elastic_ips':
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
            len(conn.get_all_load_balancers())
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
            number_of_replicas = len(entry['ReadReplicaDBInstanceIdentifiers'])
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
        """
        Main loop.
        """
        try:
            raw_using_resources = self._fetch_using_resources()
        except Exception as exception:
            raw_using_resources = dict()
            self.logger.error(
                exception.__str__()
            )
        for key, value in raw_using_resources.items():
            self._enqueue(
                AWSUsingResourceItem(
                    key=key,
                    value=value,
                    host=self.options.get('hostname')
                )
            )
        try:
            raw_limits = self._fetch_service_limit()
        except Exception as exception:
            raw_limits = dict()
            self.logger.error(
                exception.__str__()
            )
        for key, value in raw_limits.items():
            self._enqueue(
                AWSServiceLimitItem(
                    key=key,
                    value=value,
                    host=self.options.get('hostname')
                )
            )


class Validator(blackbird.plugins.base.ValidatorBase):
    """
    Validate configuration object.
    """

    def __init__(self):
        self.__spec = None

    @property
    def spec(self):
        self.__spec = (
            "[{0}]".format(__name__),
            "region_name = string()",
            "aws_access_key_id = string()",
            "aws_secret_access_key = string()",
            "hostname = string()"
        )
        return self.__spec


class AWSUsingResourceItem(blackbird.plugins.base.ItemBase):
    """
    Enqueued item object.
    """

    def __init__(self, key, value, host):
        super(AWSUsingResourceItem, self).__init__(key, value, host)

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
        self.__data['key'] = 'aws_service.using_resource.{0}'.format(self.key)
        self.__data['value'] = self.value
        self.__data['host'] = self.host
        self.__data['clock'] = self.clock


class AWSServiceLimitItem(blackbird.plugins.base.ItemBase):
    """
    Enqueued item object.
    """

    def __init__(self, key, value, host):
        super(AWSServiceLimitItem, self).__init__(key, value, host)

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
        self.__data['key'] = 'aws_service.limit.{0}'.format(self.key)
        self.__data['value'] = self.value
        self.__data['host'] = self.host
        self.__data['clock'] = self.clock


if __name__ == '__main__':
    import json
    import logging
    OPTIONS = {
        'region_name': 'us-east-1',
        'aws_access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
        'aws_secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY'
    }
    JOB = ConcreteJob(
        options=OPTIONS,
        logger=logging
    )
    print(json.dumps(JOB._fetch_using_resources()))
    print(json.dumps(JOB._fetch_service_limit()))
