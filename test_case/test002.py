from utils.otherUtils.ConnectServer.ParamikoSSH import SSHClient

Client = SSHClient()
print(Client)

connection_status  = Client.connect()
print(connection_status)



