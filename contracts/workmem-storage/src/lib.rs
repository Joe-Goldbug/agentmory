use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("3xNGfnr9cTmDQAArx5p7PcdzuS91H9Yuyx1tgU7qaMNJ");

#[program]
pub mod workmem_storage {
    use super::*;

    /// 初始化用户在链上的工作记忆配额 PDA
    pub fn initialize_quota(ctx: Context<InitializeQuota>) -> Result<()> {
        let quota = &mut ctx.accounts.user_quota;
        quota.owner = ctx.accounts.user.key();
        quota.available_commits = 0;
        quota.total_commits = 0;
        quota.last_commit_timestamp = 0;
        quota.bump = ctx.bumps.user_quota;
        Ok(())
    }

    /// 用户使用 SPL Token 购买上链存储额度 (Solana Devnet)
    pub fn buy_quota_with_tokens(
        ctx: Context<BuyQuotaWithTokens>,
        token_amount: u64,
        quota_to_add: u64,
    ) -> Result<()> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(quota_to_add > 0, ErrorCode::InvalidQuota);

        // 从用户代币账户转账到国库代币账户
        let cpi_accounts = Transfer {
            from: ctx.accounts.user_token_account.to_account_info(),
            to: ctx.accounts.treasury_token_account.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        token::transfer(cpi_ctx, token_amount)?;

        // 增加用户的可用配额
        let quota = &mut ctx.accounts.user_quota;
        quota.available_commits = quota
            .available_commits
            .checked_add(quota_to_add)
            .ok_or(ErrorCode::Overflow)?;

        emit!(QuotaPurchasedEvent {
            user: ctx.accounts.user.key(),
            token_amount,
            quota_added: quota_to_add,
            total_available: quota.available_commits,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 用户直接使用原生 SOL 购买上链存储额度 (Solana Devnet / Mainnet)
    pub fn buy_quota_with_sol(
        ctx: Context<BuyQuotaWithSol>,
        lamports: u64,
        quota_to_add: u64,
    ) -> Result<()> {
        require!(lamports > 0, ErrorCode::InvalidAmount);
        require!(quota_to_add > 0, ErrorCode::InvalidQuota);

        // 原生 SOL 转账：从用户转到国库
        let ix = anchor_lang::solana_program::system_instruction::transfer(
            &ctx.accounts.user.key(),
            &ctx.accounts.treasury.key(),
            lamports,
        );
        anchor_lang::solana_program::program::invoke(
            &ix,
            &[
                ctx.accounts.user.to_account_info(),
                ctx.accounts.treasury.to_account_info(),
                ctx.accounts.system_program.to_account_info(),
            ],
        )?;

        // 增加用户的可用配额
        let quota = &mut ctx.accounts.user_quota;
        quota.available_commits = quota
            .available_commits
            .checked_add(quota_to_add)
            .ok_or(ErrorCode::Overflow)?;

        emit!(QuotaPurchasedWithSolEvent {
            user: ctx.accounts.user.key(),
            lamports,
            quota_added: quota_to_add,
            total_available: quota.available_commits,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 提交一次不可变工作记忆快照（消耗 1 次额度并固化在链上 PDA 中）
    pub fn commit_snapshot(
        ctx: Context<CommitSnapshot>,
        project_id: [u8; 32],
        version: u32,
        snapshot_hash: [u8; 32],
        encrypted_uri: String,
        tool: String,
    ) -> Result<()> {
        let quota = &mut ctx.accounts.user_quota;
        require!(quota.available_commits > 0, ErrorCode::InsufficientQuota);

        // 扣除 1 次配额
        quota.available_commits = quota.available_commits.saturating_sub(1);
        quota.total_commits = quota.total_commits.saturating_add(1);
        quota.last_commit_timestamp = Clock::get()?.unix_timestamp;

        // 记录链上快照事实
        let snapshot = &mut ctx.accounts.snapshot_record;
        snapshot.owner = ctx.accounts.user.key();
        snapshot.project_id = project_id;
        snapshot.version = version;
        snapshot.snapshot_hash = snapshot_hash;
        snapshot.encrypted_uri = encrypted_uri;
        snapshot.tool = tool;
        snapshot.timestamp = Clock::get()?.unix_timestamp;
        snapshot.bump = ctx.bumps.snapshot_record;

        emit!(SnapshotCommittedEvent {
            owner: snapshot.owner,
            project_id,
            version,
            snapshot_hash,
            timestamp: snapshot.timestamp,
        });

        Ok(())
    }
}

// -----------------------------------------------------------------------------
// 账户结构体
// -----------------------------------------------------------------------------

#[derive(Accounts)]
pub struct InitializeQuota<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 8 + 8 + 8 + 1,
        seeds = [b"quota", user.key().as_ref()],
        bump
    )]
    pub user_quota: Account<'info, UserQuota>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct BuyQuotaWithTokens<'info> {
    #[account(
        mut,
        seeds = [b"quota", user.key().as_ref()],
        bump = user_quota.bump
    )]
    pub user_quota: Account<'info, UserQuota>,
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub user_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub treasury_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct BuyQuotaWithSol<'info> {
    #[account(
        mut,
        seeds = [b"quota", user.key().as_ref()],
        bump = user_quota.bump
    )]
    pub user_quota: Account<'info, UserQuota>,
    #[account(mut)]
    pub user: Signer<'info>,
    /// CHECK: 国库收款账户，接收原生 SOL
    #[account(mut)]
    pub treasury: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(project_id: [u8; 32], version: u32)]
pub struct CommitSnapshot<'info> {
    #[account(
        mut,
        seeds = [b"quota", user.key().as_ref()],
        bump = user_quota.bump
    )]
    pub user_quota: Account<'info, UserQuota>,
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 32 + 4 + 32 + 128 + 32 + 8 + 1,
        seeds = [b"snapshot", user.key().as_ref(), project_id.as_ref(), &version.to_le_bytes()],
        bump
    )]
    pub snapshot_record: Account<'info, SnapshotRecord>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

// -----------------------------------------------------------------------------
// 状态存储模型
// -----------------------------------------------------------------------------

#[account]
pub struct UserQuota {
    pub owner: Pubkey,               // 32 字节
    pub available_commits: u64,       // 8 字节
    pub total_commits: u64,           // 8 字节
    pub last_commit_timestamp: i64,   // 8 字节
    pub bump: u8,                     // 1 字节
}

#[account]
pub struct SnapshotRecord {
    pub owner: Pubkey,               // 32 字节
    pub project_id: [u8; 32],         // 32 字节 (Git 项目识别哈希)
    pub version: u32,                // 4 字节
    pub snapshot_hash: [u8; 32],     // 32 字节 (证据 SHA-256)
    pub encrypted_uri: String,       // ~128 字节
    pub tool: String,                // ~32 字节 (产生该快照的 AI 工具)
    pub timestamp: i64,              // 8 字节
    pub bump: u8,                    // 1 字节
}

// -----------------------------------------------------------------------------
// 事件定义
// -----------------------------------------------------------------------------

#[event]
pub struct QuotaPurchasedEvent {
    pub user: Pubkey,
    pub token_amount: u64,
    pub quota_added: u64,
    pub total_available: u64,
    pub timestamp: i64,
}

#[event]
pub struct QuotaPurchasedWithSolEvent {
    pub user: Pubkey,
    pub lamports: u64,
    pub quota_added: u64,
    pub total_available: u64,
    pub timestamp: i64,
}

#[event]
pub struct SnapshotCommittedEvent {
    pub owner: Pubkey,
    pub project_id: [u8; 32],
    pub version: u32,
    pub snapshot_hash: [u8; 32],
    pub timestamp: i64,
}

// -----------------------------------------------------------------------------
// 错误码
// -----------------------------------------------------------------------------

#[error_code]
pub enum ErrorCode {
    #[msg("代币支付数量必须大于 0")]
    InvalidAmount,
    #[msg("购买额度必须大于 0")]
    InvalidQuota,
    #[msg("配额计算溢出")]
    Overflow,
    #[msg("当前可用链上存储额度不足，请先支付代币充值额度")]
    InsufficientQuota,
}
