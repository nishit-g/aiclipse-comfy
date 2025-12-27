#!/bin/bash
# =============================================================================
# Module 03: SSH Configuration
# Sets up SSH access with key or password authentication
# SECURITY: Password is saved to file, not logged
# =============================================================================

setup_ssh() {
    log_step "Configuring SSH access..."
    
    mkdir -p ~/.ssh

    # Generate host keys if missing
    for type in rsa ecdsa ed25519; do
        local key="/etc/ssh/ssh_host_${type}_key"
        if [[ ! -f "$key" ]]; then
            ssh-keygen -t "$type" -f "$key" -q -N ''
        fi
    done

    # Setup authentication
    if [[ -n "${PUBLIC_KEY:-}" ]]; then
        echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        log_success "SSH: Public key authentication configured"
    else
        # Generate random password
        local random_pass
        random_pass=$(openssl rand -base64 12)
        echo "root:${random_pass}" | chpasswd
        
        # SECURITY FIX: Save password to secure file instead of logging
        ensure_dir "$WORKSPACE"
        local pass_file="$WORKSPACE/.ssh_password"
        echo "$random_pass" > "$pass_file"
        chmod 600 "$pass_file"
        
        log_info "SSH: Password saved to $pass_file"
        log_info "SSH: Run 'cat $pass_file' to view password"
    fi

    # Start SSH daemon
    /usr/sbin/sshd
    
    log_success "SSH daemon started"
}

# Run module
setup_ssh
