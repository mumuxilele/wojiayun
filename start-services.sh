#!/bin/bash
# Start business services
echo 'Starting business services...' >> /tmp/services-start.log

# Kill any existing instances
pkill -f 'business-userH5/app.py' 2>/dev/null
pkill -f 'business-staffH5/app.py' 2>/dev/null
pkill -f 'business-admin/app.py' 2>/dev/null
sleep 1

# Start UserH5
cd /www/wwwroot/wojiayun/business-userH5
nohup python3 app.py > /tmp/user-h5.log 2>&1 &
echo 'UserH5 started on port 22311' >> /tmp/services-start.log

# Start StaffH5
cd /www/wwwroot/wojiayun/business-staffH5
nohup python3 app.py > /tmp/staff-h5.log 2>&1 &
echo 'StaffH5 started on port 22312' >> /tmp/services-start.log

# Start Admin
cd /www/wwwroot/wojiayun/business-admin
nohup python3 app.py > /tmp/admin.log 2>&1 &
echo 'Admin started on port 22313' >> /tmp/services-start.log

echo 'All services started' >> /tmp/services-start.log
