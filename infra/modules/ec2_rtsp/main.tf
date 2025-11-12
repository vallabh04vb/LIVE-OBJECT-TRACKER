locals {
  user_data = <<-EOT
              #!/bin/bash
              set -euxo pipefail
              dnf update -y
              dnf install -y docker git
              systemctl enable docker
              systemctl start docker
              usermod -a -G docker ec2-user
              mkdir -p /opt/rtsp
              cd /opt/rtsp
              curl -L -o demo.mp4 "${var.video_url}"
              cat <<'SCRIPT' > docker-compose.yaml
              version: '3.8'
              services:
                rtsp:
                  image: aler9/rtsp-simple-server:latest
                  ports:
                    - "8554:8554"
                  volumes:
                    - ./demo.mp4:/media/demo.mp4:ro
                  command: ["/rtsp-simple-server", "/config.yml"]
                  restart: unless-stopped
              SCRIPT

              cat <<'CFG' > config.yml
              paths:
                mystream:
                  source: file:///media/demo.mp4
                  runOnInit: yes
                  runOnInitRestart: yes
              CFG

              docker run -d \
                --name rtsp-simple-server \
                -p 8554:8554 \
                -v /opt/rtsp/demo.mp4:/media/demo.mp4:ro \
                -v /opt/rtsp/config.yml:/config.yml:ro \
                aler9/rtsp-simple-server:latest
              EOT
}

resource "aws_instance" "this" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  key_name               = length(var.ssh_key_name) > 0 ? var.ssh_key_name : null

  user_data = base64encode(local.user_data)

  tags = {
    Name = "${var.project_name}-rtsp"
  }
}
