resource "aws_security_group" "broker" {
  name        = "${var.project_name}-msk-broker"
  description = "Security group for MSK broker nodes"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-msk-broker"
  }
}

resource "aws_msk_cluster" "this" {
  cluster_name           = "${var.project_name}-msk"
  kafka_version          = var.kafka_version
  number_of_broker_nodes = length(var.subnet_ids)

  broker_node_group_info {
    instance_type   = var.broker_instance_type
    client_subnets  = var.subnet_ids
    security_groups = concat([aws_security_group.broker.id], var.client_security_group_ids)

    storage_info {
      ebs_storage_info {
        volume_size = var.broker_ebs_volume_size
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  enhanced_monitoring = "PER_TOPIC_PER_PARTITION"

  tags = {
    Name = "${var.project_name}-msk"
  }
}
