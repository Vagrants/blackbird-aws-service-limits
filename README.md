blackbird-aws-service-limits
============================

![Cicle CI build status](https://circleci.com/gh/Vagrants/blackbird-aws-service-limits/tree/master.svg?style=shield&circle-token=:9bf6260934b1850def5009ac2a85c6e8a9643d7a)

Blackbird AWS(Amazon Web Service) service limits plugin.
This plugin gets following AWS resource limitations.

The following resource list is created based on [AWS service limits page](http://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html).

| Resource name | Current number of using | Limits |
|---------------|-------------------------|--------|
| autoscale launch configurations                | :o: | :o: |
| autoscale groups                               | :o: | :o: |
| EC2 EIP                                        | :o: | :o: |
| EC2 running instances                          | :o: | :o: |
| number of ELBs                                 | :o: | :x: |
| RDS instances                                  | :o: | :x: |
| RDS total storage                              | :o: | :x: |
| RDS read replicas per master                   | :o: | :x: |
| DynamoDB read capacity units individual table  | :o: | :x: |
| DynamoDB write capacity units individual table | :o: | :x: |
| DynamoDB read capacity units per account       | :o: | :x: |
| DynamoDB write capacity units per account      | :o: | :x: |
