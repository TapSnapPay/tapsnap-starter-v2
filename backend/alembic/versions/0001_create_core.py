"""create core tables

Revision ID: 0001_create_core
Revises: 
Create Date: 2025-08-11 16:51:05
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_core'
down_revision = None

def upgrade() -> None:
    op.create_table('merchants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('platform_account', sa.String(length=100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_merchants_email', 'merchants', ['email'], unique=True)
    op.create_index('ix_merchants_id', 'merchants', ['id'], unique=False)

    op.create_table('transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='created'),
        sa.Column('psp_reference', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'], unique=False)
    op.create_index('ix_transactions_merchant_id', 'transactions', ['merchant_id'], unique=False)

    op.create_table('payouts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='scheduled'),
        sa.Column('scheduled_for', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_payouts_id', 'payouts', ['id'], unique=False)
    op.create_index('ix_payouts_merchant_id', 'payouts', ['merchant_id'], unique=False)

def downgrade() -> None:
    op.drop_table('payouts')
    op.drop_index('ix_transactions_merchant_id', table_name='transactions')
    op.drop_index('ix_transactions_id', table_name='transactions')
    op.drop_table('transactions')
    op.drop_index('ix_merchants_id', table_name='merchants')
    op.drop_index('ix_merchants_email', table_name='merchants')
    op.drop_table('merchants')
