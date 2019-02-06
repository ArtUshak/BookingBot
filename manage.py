#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script for booking database management."""
import logging

import click

import botsettings
import booking
import models


logging.basicConfig(format='%(message)s')

logger = logging.getLogger('management')


@click.group()
def cli():
    """Run command line."""
    pass


@click.command()
@click.argument('admins_file', type=click.File('rt'))
def load_admins(admins_file):
    """Load administrator list from file to database."""
    admin_user_ids = set()
    for line in admins_file:
        data: str = line.strip()
        if len(data) == 0:
            continue
        if data[0] == '#':
            continue
        admin_user_ids.add(int(data))

    models.db_init(botsettings.database_file)
    with models.db_proxy.transaction():
        existing_admins = models.User.select().where(
            models.User.user_id << admin_user_ids
        )
        models.User.update(
            is_admin=True, is_whitelisted=True
        ).where(
            models.User.user_id << admin_user_ids
        ).execute()
        new_admin_ids = admin_user_ids - \
            {x.user_id for x in existing_admins}
        if len(new_admin_ids) > 0:
            models.User.bulk_create(
                [models.User(
                    user_id=user_id, chat_id=None, username=None,
                    is_admin=True, is_whitelisted=True)
                 for user_id in new_admin_ids])


@click.command()
@click.argument('whitelist_file', type=click.File('rt'))
def load_whitelist(whitelist_file):
    """Load whitelist from file to database."""
    whitelist_user_ids = set()
    for line in whitelist_file:
        data: str = line.strip()
        if len(data) == 0:
            continue
        if data[0] == '#':
            continue
        whitelist_user_ids.add(int(data))

    models.db_init(botsettings.database_file)
    with models.db_proxy.transaction():
        existing_whitelist_users = models.User.select().where(
            models.User.user_id << whitelist_user_ids
        )
        models.User.update(
            is_whitelisted=True
        ).where(
            models.User.user_id << whitelist_user_ids
        ).execute()
        new_whitelist_user_ids = whitelist_user_ids - \
            {x.user_id for x in existing_whitelist_users}
        if len(new_whitelist_user_ids) > 0:
            models.User.bulk_create(
                [models.User(
                    user_id=user_id, chat_id=None, username=None,
                    is_whitelisted=True)
                 for user_id in new_whitelist_user_ids])


@click.command()
@click.argument('username', type=click.STRING)
def op_username(username):
    """Make user with given username admin."""
    models.db_init(botsettings.database_file)
    with models.db_proxy.transaction():
        try:
            user = models.User.get(username=username)
            user.is_admin = True
            user.is_whitelisted = True
            user.save()
        except models.User.DoesNotExist:
            logger.info('User {} not found in database'.format(username))


@click.command()
@click.argument('username', type=click.STRING)
def deop_username(username):
    """Make user with given username admin."""
    models.db_init(botsettings.database_file)
    with models.db_proxy.transaction():
        try:
            user = models.User.get(username=username)
            user.is_admin = False
            user.save()
        except models.User.DoesNotExist:
            logger.info('User {} not found in database'.format(username))


cli.add_command(load_admins)
cli.add_command(load_whitelist)
cli.add_command(op_username)
cli.add_command(deop_username)

if __name__ == '__main__':
    cli()
