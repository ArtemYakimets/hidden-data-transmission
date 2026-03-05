# -*- mode: ruby -*-
# vi: set ft=ruby :

# Lab stand: covert channel based on packet length manipulation
# P1 (sender + bookmark) -> UZ (security device) -> P2 (receiver / attacker)

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "512"
    vb.cpus = 1
    vb.gui = false
  end

  config.vm.synced_folder "./scripts", "/home/vagrant/scripts"

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update -y
    apt-get install -y python3
    ufw disable 2>/dev/null || true
  SHELL

  config.vm.define "p1" do |node|
    node.vm.hostname = "p1"
    node.vm.network "private_network", ip: "192.168.56.10"
  end

  config.vm.define "uz" do |node|
    node.vm.hostname = "uz"
    node.vm.network "private_network", ip: "192.168.56.11"
  end

  config.vm.define "p2" do |node|
    node.vm.hostname = "p2"
    node.vm.network "private_network", ip: "192.168.56.12"
  end
end
