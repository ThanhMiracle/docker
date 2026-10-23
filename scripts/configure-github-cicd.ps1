param(
    [string]$Repository = 'ThanhMiracle/docker',
    [string]$ProductionReviewer = 'ThanhMiracle',
    [ValidateRange(0, 6)][int]$PullRequestApprovals = 0
)
$ErrorActionPreference = 'Stop'

function Invoke-GitHubJson {
    param([string]$Method, [string]$Endpoint, [object]$Body)
    $bodyPath = Join-Path ([IO.Path]::GetTempPath()) ('cicd-github-' + [guid]::NewGuid() + '.json')
    try {
        [IO.File]::WriteAllText($bodyPath, ($Body | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
        & gh api --method $Method $Endpoint --input $bodyPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "GitHub request failed: $Method $Endpoint" }
    } finally {
        Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
    }
}

$reviewerId = & gh api "users/$ProductionReviewer" --jq '.id'
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve production reviewer' }

Invoke-GitHubJson PUT "repos/$Repository/environments/production" @{
    wait_timer = 0
    prevent_self_review = $false
    can_admins_bypass = $false
    reviewers = @(@{ type = 'User'; id = [long]$reviewerId })
    deployment_branch_policy = @{ protected_branches = $false; custom_branch_policies = $true }
}

$branchPoliciesRaw = & gh api "repos/$Repository/environments/production/deployment-branch-policies"
if ($LASTEXITCODE -ne 0) { throw 'Cannot read production deployment branch policies' }
$branchPolicies = $branchPoliciesRaw | ConvertFrom-Json
if (-not ($branchPolicies.branch_policies | Where-Object { $_.name -eq 'main' -and $_.type -eq 'branch' })) {
    Invoke-GitHubJson POST "repos/$Repository/environments/production/deployment-branch-policies" @{
        name = 'main'; type = 'branch'
    }
}

Invoke-GitHubJson PUT "repos/$Repository/branches/main/protection" @{
    required_status_checks = @{ strict = $true; contexts = @('Quality Gate') }
    enforce_admins = $true
    required_pull_request_reviews = @{
        dismiss_stale_reviews = $true
        require_code_owner_reviews = $false
        required_approving_review_count = $PullRequestApprovals
        require_last_push_approval = ($PullRequestApprovals -gt 0)
    }
    restrictions = $null
    required_conversation_resolution = $true
    allow_force_pushes = $false
    allow_deletions = $false
}

# PATCH existing variables instead of failing on repeated setup.
$variablesRaw = & gh api "repos/$Repository/actions/variables"
if ($LASTEXITCODE -ne 0) { throw 'Cannot read Actions variables' }
$variables = $variablesRaw | ConvertFrom-Json
if ($variables.variables | Where-Object { $_.name -eq 'PRODUCTION_TARGET' }) {
    $variableMethod = 'PATCH'
} else {
    $variableMethod = 'POST'
}
$variableEndpoint = "repos/$Repository/actions/variables"
if ($variableMethod -eq 'PATCH') { $variableEndpoint += '/PRODUCTION_TARGET' }
Invoke-GitHubJson $variableMethod $variableEndpoint @{ name = 'PRODUCTION_TARGET'; value = 'container-apps' }

Write-Output "Configured main protection and production approval for $ProductionReviewer."
Write-Output "PR approval count: $PullRequestApprovals. Azure/ACR secrets must be added separately."
