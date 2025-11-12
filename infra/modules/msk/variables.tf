variable "project_name" {
  type = string
}

variable "vpc_id" {
  description = "VPC where MSK will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for MSK brokers"
  type        = list(string)
}

variable "kafka_version" {
  type    = string
  default = "3.5.1"
}

variable "broker_instance_type" {
  type = string
}

variable "broker_ebs_volume_size" {
  type    = number
  default = 20
}

variable "client_security_group_ids" {
  description = "Additional security group IDs for client access"
  type        = list(string)
  default     = []
}
