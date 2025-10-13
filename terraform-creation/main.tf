############################################
# main.tf — Create N Ubuntu VMs with Docker
############################################

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.40.0"
    }
  }
}

variable "subscription_id" { type = string }

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

############################
# ====== VARIABLES ======  #
############################

variable "prefix" {
  description = "Name prefix for all resources"
  type        = string
  default     = "docker-vm"
}

variable "location" {
  description = "Azure region (e.g. East Asia, Southeast Asia, East US)"
  type        = string
  default     = "East Asia"
}

variable "admin_username" {
  description = "Linux admin username"
  type        = string
  default     = "thanh"
}

variable "ssh_public_key" {
  description = "Your SSH public key (e.g. from ~/.ssh/id_rsa.pub)"
  type        = string
}

variable "vm_size" {
  description = "VM size"
  type        = string
  default     = "Standard_D2s_v3"
}

# NEW: how many identical VMs to create
variable "vm_count" {
  description = "Number of identical VMs to create"
  type        = number
  default     = 2
}

############################
# ===== SHARED RESOURCES ==#
############################

resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-rg"
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "${var.prefix}-vnet"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.10.0.0/16"]
}

resource "azurerm_subnet" "subnet" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "Allow-SSH"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # HTTP
  security_rule {
    name                       = "Allow-HTTP"
    priority                   = 1010
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # HTTPS
  security_rule {
    name                       = "Allow-HTTPS"
    priority                   = 1020
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

############################
# === PER-VM RESOURCES ====#
############################

resource "azurerm_public_ip" "pip" {
  count               = var.vm_count
  name                = "${var.prefix}-pip-${count.index + 1}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "nic" {
  count               = var.vm_count
  name                = "${var.prefix}-nic-${count.index + 1}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip[count.index].id
  }
}

resource "azurerm_network_interface_security_group_association" "nic_nsg" {
  count                     = var.vm_count
  network_interface_id      = azurerm_network_interface.nic[count.index].id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_linux_virtual_machine" "vm" {
  count               = var.vm_count
  name                = "${var.prefix}-${count.index + 1}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = var.vm_size
  admin_username      = var.admin_username
  network_interface_ids = [azurerm_network_interface.nic[count.index].id]

  # Ubuntu 24.04 LTS (canonical/ubuntu-24_04-lts/server)
  source_image_reference {
    publisher = "canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"  # có thể pin: "24.04.202510010"
  }

  os_disk {
    name                 = "${var.prefix}-osdisk-${count.index + 1}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 30
  }

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  custom_data = base64encode(
    templatefile("${path.module}/cloud-init.yaml.tftpl", {
      username  = var.admin_username
      public_ip = azurerm_public_ip.pip[count.index].ip_address
    })
  )

  tags = {
    project = var.prefix
    role    = "docker-host"
    node    = tostring(count.index + 1)
  }
}

############################
# ======= OUTPUTS ======== #
############################

output "public_ips" {
  description = "Public IPs of all VMs"
  value       = azurerm_public_ip.pip[*].ip_address
}

output "ssh_commands" {
  description = "SSH commands for all VMs"
  value       = [
    for ip in azurerm_public_ip.pip[*].ip_address :
    "ssh ${var.admin_username}@${ip}"
  ]
}
