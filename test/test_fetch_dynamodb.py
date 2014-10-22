#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import boto.dynamodb2.fields
import boto.dynamodb2.table

import moto.dynamodb2
import nose.tools

import aws_service_limits


class TestFetchUsingDynamoDBResources(object):

    def __init__(self):
        self.options = {
            'region_name': 'us-east-1'
        }
        self.conn = None
        self.concrete_job = aws_service_limits.ConcreteJob(
            options=self.options,
            logger=logging
        )

    @moto.dynamodb2.mock_dynamodb2
    def setup(self):
        self.conn = boto.dynamodb2.connect_to_region(
            region_name='us-east-1'
        )

    def create_table(self,
                     table_name='TEST_FETCH_DYNAMODB',
                     read_units=10,
                     write_units=10):
        return boto.dynamodb2.table.Table.create(
            table_name=table_name,
            schema=[
                boto.dynamodb2.fields.HashKey('test_fetch_dynamodb')
            ],
            throughput={
                'read': read_units,
                'write': write_units
            }
        )

    @moto.dynamodb2.mock_dynamodb2
    def test_not_use_dynamodb(self):
        result = self.concrete_job._fetch_using_dynamodb_resources()
        expected_result = {
            'dynamodb.read_capacity_units_individual_table': 0,
            'dynamodb.write_capacity_units_individual_table': 0,
            'dynamodb.read_capacity_units_per_account': 0,
            'dynamodb.write_capacity_units_per_account': 0
        }
        logging.debug(result)
        nose.tools.eq_(
            result, expected_result
        )

    @moto.dynamodb2.mock_dynamodb2
    def test_use_one_table(self):
        table_name = 'TEST_FETCH_DYNAMODB'
        self.create_table(table_name=table_name)
        logging.debug(
            self.conn.describe_table(table_name)
        )

        result = self.concrete_job._fetch_using_dynamodb_resources()
        expected_result = {
            'dynamodb.read_capacity_units_individual_table': 10,
            'dynamodb.write_capacity_units_individual_table': 10,
            'dynamodb.read_capacity_units_per_account': 10,
            'dynamodb.write_capacity_units_per_account': 10
        }
        logging.debug(result)
        nose.tools.eq_(
            result, expected_result
        )

    @moto.dynamodb2.mock_dynamodb2
    def test_use_two_tables(self):
        table_names = [
            'TEST_FETCH_DYNAMODB_001',
            'TEST_FETCH_DYNAMODB_002'
        ]
        self.create_table(
            table_name=table_names[0],
            read_units=10,
            write_units=10
        )
        self.create_table(
            table_name=table_names[1],
            read_units=20,
            write_units=10
        )
        for entry in table_names:
            logging.debug(
                self.conn.describe_table(entry)
            )

        result = self.concrete_job._fetch_using_dynamodb_resources()
        expected_result = {
            'dynamodb.read_capacity_units_individual_table': 20,
            'dynamodb.write_capacity_units_individual_table': 10,
            'dynamodb.read_capacity_units_per_account': 30,
            'dynamodb.write_capacity_units_per_account': 20
        }
        logging.debug(result)
        nose.tools.eq_(
            result, expected_result
        )
