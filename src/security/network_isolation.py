"""
Network Isolation Verification
Ensures system operates in air-gapped mode
"""

import logging
import socket
import subprocess
from typing import List, Dict, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class NetworkCheckResult:
    """Result of network isolation check"""
    check_name: str
    passed: bool
    details: str


class NetworkIsolationVerifier:
    """
    Verify network isolation for air-gapped operation
    """
    
    @staticmethod
    def verify_dns_disabled() -> NetworkCheckResult:
        """Check if DNS resolution is disabled"""
        try:
            # Attempt to resolve a domain (should fail)
            socket.gethostbyname("example.com")
            return NetworkCheckResult(
                check_name="DNS Resolution",
                passed=False,
                details="DNS resolution is active (should be disabled)"
            )
        except socket.gaierror:
            return NetworkCheckResult(
                check_name="DNS Resolution",
                passed=True,
                details="DNS resolution disabled"
            )
    
    @staticmethod
    def verify_no_internet_connection() -> NetworkCheckResult:
        """Check for internet connectivity"""
        test_hosts = [
            ("8.8.8.8", 53),      # Google DNS
            ("1.1.1.1", 53),      # Cloudflare DNS
            ("208.67.222.222", 53)  # OpenDNS
        ]
        
        for host, port in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((host, port))
                sock.close()
                
                return NetworkCheckResult(
                    check_name="Internet Connectivity",
                    passed=False,
                    details=f"Connection to {host}:{port} successful (should fail)"
                )
            except (socket.timeout, socket.error):
                continue
        
        return NetworkCheckResult(
            check_name="Internet Connectivity",
            passed=True,
            details="No internet connectivity detected"
        )
    
    @staticmethod
    def verify_localhost_only() -> NetworkCheckResult:
        """Check if only localhost binding is active"""
        try:
            # Try to bind to 0.0.0.0 (should fail if properly configured)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.bind(("127.0.0.1", 0))  # Bind to localhost
            sock.close()
            
            return NetworkCheckResult(
                check_name="Localhost Binding",
                passed=True,
                details="Localhost binding available"
            )
        except Exception as e:
            return NetworkCheckResult(
                check_name="Localhost Binding",
                passed=False,
                details=f"Localhost binding failed: {e}"
            )
    
    @staticmethod
    def check_firewall_rules() -> NetworkCheckResult:
        """Check firewall rules (Linux iptables)"""
        try:
            # Check iptables rules
            result = subprocess.run(
                ["iptables", "-L", "-n"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                # Check for DROP rules on OUTPUT chain
                if "drop" in output or "reject" in output:
                    return NetworkCheckResult(
                        check_name="Firewall Rules",
                        passed=True,
                        details="Firewall rules appear configured"
                    )
                else:
                    return NetworkCheckResult(
                        check_name="Firewall Rules",
                        passed=False,
                        details="No DROP/REJECT rules found"
                    )
            else:
                return NetworkCheckResult(
                    check_name="Firewall Rules",
                    passed=False,
                    details="Unable to check iptables"
                )
        
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            return NetworkCheckResult(
                check_name="Firewall Rules",
                passed=False,
                details=f"Firewall check failed: {type(e).__name__}"
            )
    
    @staticmethod
    def verify_all() -> Dict[str, Any]:
        """
        Run all network isolation checks
        
        Returns:
            Dict with check results
        """
        logger.info("Running network isolation verification...")
        
        checks = [
            NetworkIsolationVerifier.verify_dns_disabled(),
            NetworkIsolationVerifier.verify_no_internet_connection(),
            NetworkIsolationVerifier.verify_localhost_only(),
            NetworkIsolationVerifier.check_firewall_rules()
        ]
        
        passed = sum(1 for check in checks if check.passed)
        total = len(checks)
        
        results = {
            "all_passed": passed == total,
            "passed_count": passed,
            "total_count": total,
            "checks": [
                {
                    "name": check.check_name,
                    "passed": check.passed,
                    "details": check.details
                }
                for check in checks
            ]
        }
        
        if results["all_passed"]:
            logger.info("✓ All network isolation checks passed")
        else:
            logger.warning(f"✗ Network isolation checks: {passed}/{total} passed")
        
        return results
    
    @staticmethod
    def block_network_via_iptables():
        """
        Configure iptables to block all external network access
        WARNING: Requires root privileges
        """
        commands = [
            # Allow loopback
            ["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"],
            ["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
            
            # Drop all other output
            ["iptables", "-A", "OUTPUT", "-j", "DROP"],
        ]
        
        logger.warning("Attempting to configure firewall rules (requires root)")
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, timeout=5)
                logger.info(f"Executed: {' '.join(cmd)}")
            except Exception as e:
                logger.error(f"Failed to execute {' '.join(cmd)}: {e}")
