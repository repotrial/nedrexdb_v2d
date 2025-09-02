#!/bin/bash

# The path to your neo4j.conf file
NEO4J_CONF="/var/lib/neo4j/conf/neo4j.conf"

# The desired number of allowed failed authentication attempts
MAX_FAILED_ATTEMPTS=100

if grep -q "^#*dbms.security.auth_enabled=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.security.auth_enabled=.*/dbms.security.auth_enabled=false/g" "$NEO4J_CONF"
else
    echo "dbms.security.auth_enabled=false" >> "$NEO4J_CONF"
fi

# Uncomment the dbms.security.auth_max_failed_attempts line and set its value
if grep -q "^#*dbms.security.auth_max_failed_attempts=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.security.auth_max_failed_attempts=.*/dbms.security.auth_max_failed_attempts=$MAX_FAILED_ATTEMPTS/g" "$NEO4J_CONF"
else
    echo "dbms.security.auth_max_failed_attempts=$MAX_FAILED_ATTEMPTS" >> "$NEO4J_CONF"
fi

# Enable Bolt connector
if grep -q "^#*dbms.connector.bolt.enabled=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.connector.bolt.enabled=.*/dbms.connector.bolt.enabled=true/g" "$NEO4J_CONF"
else
    echo "dbms.connector.bolt.enabled=true" >> "$NEO4J_CONF"
fi
echo "Bolt connector enabled in neo4j.conf."

# Enable HTTP connector
if grep -q "^#*dbms.connector.http.enabled=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.connector.http.enabled=.*/dbms.connector.http.enabled=true/g" "$NEO4J_CONF"
else
    echo "dbms.connector.http.enabled=true" >> "$NEO4J_CONF"
fi
echo "HTTP connector enabled in neo4j.conf."

# Unrestrict APOC procedures
if grep -q "dbms.security.procedures.unrestricted=apoc.*,genai.*,vectorize.*" "$NEO4J_CONF"; then
    echo "APOC procedures already unrestricted in neo4j.conf."
else
    echo 'dbms.security.procedures.unrestricted=apoc.*,genai.*,vectorize.*' >> "$NEO4J_CONF"
    echo "Updated neo4j.conf to allow unrestricted APOC procedures."
fi

# Set Bolt connector listen address
if grep -q "^#*dbms.connector.bolt.listen_address=" "$NEO4J_CONF"; then
    sed -i 's/^#*dbms.connector.bolt.listen_address=.*/dbms.connector.bolt.listen_address=0.0.0.0:7687/g' "$NEO4J_CONF"
else
    echo "dbms.connector.bolt.listen_address=0.0.0.0:7687" >> "$NEO4J_CONF"
fi
echo "Bolt connector listen address set to 0.0.0.0:7687."

# Set HTTP connector listen address
if grep -q "^#*dbms.connector.http.listen_address=" "$NEO4J_CONF"; then
    sed -i 's/^#*dbms.connector.http.listen_address=.*/dbms.connector.http.listen_address=0.0.0.0:7474/g' "$NEO4J_CONF"
else
    echo "dbms.connector.http.listen_address=0.0.0.0:7474" >> "$NEO4J_CONF"
fi
echo "HTTP connector listen address set to 0.0.0.0:7474."

# Set Bolt connector TLS level to DISABLED
if grep -q "^#*dbms.connector.bolt.tls_level=" "$NEO4J_CONF"; then
    sed -i "s/^#*dbms.connector.bolt.tls_level=.*/dbms.connector.bolt.tls_level=DISABLED/g" "$NEO4J_CONF"
else
    echo "dbms.connector.bolt.tls_level=DISABLED" >> "$NEO4J_CONF"
fi
echo "Bolt connector TLS level set to DISABLED."


# Enable Bolt over WebSocket
#if grep -q "^#*dbms.connector.bolt.ws.enabled=" "$NEO4J_CONF"; then
#    sed -i "s/^#*dbms.connector.bolt.ws.enabled=.*/dbms.connector.bolt.ws.enabled=true/g" "$NEO4J_CONF"
#else
#    echo "dbms.connector.bolt.ws.enabled=true" >> "$NEO4J_CONF"
#fi
#echo "Bolt over WebSocket enabled."

# Set Bolt over WebSocket listen address
#if grep -q "^#*dbms.connector.bolt.ws.listen_address=" "$NEO4J_CONF"; then
#    sed -i "s/^#*dbms.connector.bolt.ws.listen_address=.*/dbms.connector.bolt.ws.listen_address=0.0.0.0:7687/g" "$NEO4J_CONF"
#else
#    echo "dbms.connector.bolt.ws.listen_address=0.0.0.0:7687" >> "$NEO4J_CONF"
#fi
#echo "Bolt over WebSocket listen address set to 0.0.0.0:7687."


# Remove deprecated settings
#sed -i 's/^#*dbms.default_listen_address=.*/# Deprecated setting removed/g'  "$NEO4J_CONF"

# Add new settings for default listen address
if ! grep -q "^server.default_listen_address="  "$NEO4J_CONF"; then
    echo "server.default_listen_address=0.0.0.0" >> "$NEO4J_CONF"
    echo "Added new default listen address configuration."
fi

# Add new settings for Bolt listen address
if ! grep -q "^server.bolt.listen_address="  "$NEO4J_CONF"; then
    echo "server.bolt.listen_address=0.0.0.0:7687" >> "$NEO4J_CONF"
    echo "Added new Bolt listen address configuration."
fi

