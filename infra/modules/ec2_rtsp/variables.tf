variable "project_name" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "security_group_ids" {
  type = list(string)
}

variable "ami_id" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "video_url" {
  type = string
}

variable "ssh_key_name" {
  type    = string
  default = ""
}
