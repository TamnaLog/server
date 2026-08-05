param(
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string] $Location,

    [Parameter(Mandatory = $true)]
    [string] $AppName,

    [Parameter(Mandatory = $true)]
    [string] $AcrName,

    [Parameter(Mandatory = $true)]
    [string] $MysqlServerName,

    [Parameter(Mandatory = $true)]
    [string] $MysqlAdminUser,

    [Parameter(Mandatory = $true)]
    [string] $MysqlAdminPassword,

    [string] $MysqlDatabase = "tour",
    [string] $PlanName = "jamkkan-jeju-api-plan",
    [string] $Sku = "B1",
    [string] $ImageName = "jamkkan-jeju-api",
    [string] $Tag = "latest",
    [string] $KtoBaseUrl = "https://apis.data.go.kr/B551011/KorService2",
    [Parameter(Mandatory = $true)]
    [string] $KtoServiceKey,
    [string] $KtoMobileOs = "ETC",
    [string] $KtoMobileApp = "tour-api"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating resource group..."
az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

Write-Host "Creating Azure Container Registry..."
az acr create `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --sku Basic `
    --admin-enabled true `
    --output none

Write-Host "Building image in Azure Container Registry..."
docker build --tag "$AcrName.azurecr.io/$ImageName`:$Tag" .

Write-Host "Logging in to Azure Container Registry..."
az acr login `
    --name $AcrName `
    --output none

Write-Host "Pushing image to Azure Container Registry..."
docker push "$AcrName.azurecr.io/$ImageName`:$Tag"

$AcrLoginServer = az acr show `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --query loginServer `
    --output tsv

$AcrUsername = az acr credential show `
    --name $AcrName `
    --query username `
    --output tsv

$AcrPassword = az acr credential show `
    --name $AcrName `
    --query "passwords[0].value" `
    --output tsv

Write-Host "Creating Azure Database for MySQL Flexible Server..."
az mysql flexible-server create `
    --resource-group $ResourceGroup `
    --name $MysqlServerName `
    --location $Location `
    --admin-user $MysqlAdminUser `
    --admin-password $MysqlAdminPassword `
    --sku-name Standard_B1ms `
    --tier Burstable `
    --version 8.0.21 `
    --public-access 0.0.0.0 `
    --output none

Write-Host "Creating MySQL database..."
az mysql flexible-server db create `
    --resource-group $ResourceGroup `
    --server-name $MysqlServerName `
    --database-name $MysqlDatabase `
    --output none

Write-Host "Creating App Service plan..."
az appservice plan create `
    --resource-group $ResourceGroup `
    --name $PlanName `
    --is-linux `
    --sku $Sku `
    --output none

Write-Host "Creating Web App for container..."
az webapp create `
    --resource-group $ResourceGroup `
    --plan $PlanName `
    --name $AppName `
    --deployment-container-image-name "$AcrLoginServer/$ImageName`:$Tag" `
    --output none

Write-Host "Configuring container registry credentials..."
az webapp config container set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --container-image-name "$AcrLoginServer/$ImageName`:$Tag" `
    --container-registry-url "https://$AcrLoginServer" `
    --container-registry-user $AcrUsername `
    --container-registry-password $AcrPassword `
    --output none

Write-Host "Configuring app settings..."
az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --settings `
        WEBSITES_PORT=8000 `
        APP_NAME=jamkkan-jeju-api `
        ENVIRONMENT=production `
        DEBUG=false `
        MYSQL_HOST="$MysqlServerName.mysql.database.azure.com" `
        MYSQL_PORT=3306 `
        MYSQL_DATABASE=$MysqlDatabase `
        MYSQL_USER=$MysqlAdminUser `
        MYSQL_PASSWORD=$MysqlAdminPassword `
        MYSQL_SSL_ENABLED=true `
        KTO_BASE_URL=$KtoBaseUrl `
        KTO_SERVICE_KEY=$KtoServiceKey `
        KTO_MOBILE_OS=$KtoMobileOs `
        KTO_MOBILE_APP=$KtoMobileApp `
    --output none

Write-Host "Restarting Web App..."
az webapp restart `
    --resource-group $ResourceGroup `
    --name $AppName `
    --output none

Write-Host "Done: https://$AppName.azurewebsites.net"
