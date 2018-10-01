import asyncio
# import uvloop
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
import logging
import os
import random
import re   #regex

from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.utils import exceptions
from aiogram.utils import executor

import psycopg2
import pytoml as toml

#////////////////////////////////////////////////#
#////////////////////////////////////////////////#

class Config(object):
    def __init__(self, config_filename):
        self.config_filename = config_filename

        with open(config_filename, 'r') as config_file:
            cf = toml.load(config_file)
            #load credentials
            self.bot_token = cf['credentials']['bot_token']
            self.db_name = cf['credentials']['db_name']
            self.db_uname = cf['credentials']['db_uname']
            self.db_pass = cf['credentials']['db_pass']

            #load bot owner
            self.bot_owner = cf['owner']['owner_id']

            #load bind and ban list
            self.bot_bind = cf['settings']['chat_id_bind']
            self.bot_ban = cf['settings']['chat_id_ban']

#////////////////////////////////////////////////#
#////////////////////////////////////////////////#

logging.basicConfig(level=logging.INFO)

os.system('cls' if os.name == 'nt' else 'clear')    #clear screen
print('// Starting bot. Please wait. . .')

config = Config('config.toml')  #load config
loop = asyncio.get_event_loop()
storage = MemoryStorage()
# try:
#     fenrir = Bot(token=config.bot_token, validate_token=true)
#     # if fails, raises: aiogram.utils.exceptions.ValidationError
# except exceptions.ValidationError:
#     pass
fenrir = Bot(token=config.bot_token, loop=loop)
fenrir_disp = Dispatcher(fenrir, storage=storage)

#load bot profile data
get_bot_info = loop.create_task(fenrir.get_me())
bot_user = loop.run_until_complete(get_bot_info)
fenrir_id = bot_user.id
fenrir_is_bot = bot_user.is_bot
fenrir_first_name = bot_user.first_name
fenrir_last_name = bot_user.last_name
fenrir_username = bot_user.username
fenrir_language_code = bot_user.language_code


db_conn = psycopg2.connect(dbname=config.db_name, user=config.db_uname, password=config.db_pass)
db_curs = db_conn.cursor()


#////////////////////////////////////////////////#
#////////////////////////////////////////////////#


def admin_only(func):
    def isadmin(invoker, chatadmins):
        adminids = []
        for admin in chatadmins:
            adminids.append(admin.user.id)
        return invoker.id in adminids

    async def wrapper(message: types.Message):
        invoker = message.from_user
        chatadmins = await message.chat.get_administrators()
        if isadmin(invoker, chatadmins):
            await func(message)
            # print('isadmin')
            #tell that an admin thing is performed
            pass
        else:
            # print('notadmin')
            #tell that an admin thing is denied
            pass

    return wrapper


def owner_only(func):
    async def wrapper(message: types.Message):
        invokerid = message.from_user.id
        ownerid = config.bot_owner
        if invokerid == ownerid:
            await func(message)
            # print('isowner')
            #tell that an admin thing is performed
            pass
        else:
            # print('notowner')
            #tell that an admin thing is denied
            pass

    return wrapper


def group_only(func):
    async def wrapper(message: types.Message):
        if message.chat.type in ['group', 'supergroup']:
            await func(message)
            # print('isgroup')
            #tell that an admin thing is performed
            pass
        else:
            # print('notgroup')
            #tell that an admin thing is denied
            pass

    return wrapper


def supergroup_only(func):
    async def wrapper(message: types.Message):
        if message.chat.type == 'supergroup':
            await func(message)
            # print('isgroup')
            #tell that an admin thing is performed
            pass
        else:
            # print('notgroup')
            #tell that an admin thing is denied
            pass

    return wrapper



class CMD_handler:
    """docstring for CMD_handler"""
    def __init__(self, message: types.Message):
        super(CMD_handler, self).__init__()
        self.message = message
        
    async def echo(message: types.Message):
        # print(f'[CMD] {message.from_user.first_name} in pass: {message.text}')
        await message.reply(message.text)

    async def deleteme(message: types.Message):
        # print(f'[CMD] {message.from_user.first_name} in pass: {message.text}')
        await message.delete()

    # @owner_only
    # @admin_only
    async def membercount(message: types.Message):
        membercount = await message.chat.get_members_count()
        await message.reply(f'There are {membercount} members here.')

    @group_only
    async def chatadmins(message: types.Message):
        chatadmins = await message.chat.get_administrators()
        admins = ''
        adminct = 0
        for admin in chatadmins:
            if not admin.user.is_bot:
                admins = admins + ' @' + admin.user.username
                adminct = adminct + 1

        reply = 'The ' + ('admin' if adminct==1 else 'admins') + ' of this chat ' + ('is' if adminct==1 else 'are')
        await message.reply(reply + admins)

    @group_only
    @admin_only
    async def getlink(message: types.Message):
        chatlink = await message.chat.get_url()
        if chatlink == None:
            chatlink = await message.chat.export_invite_link()
        invokerid = message.from_user.id
        await message.reply('Order received. Check your PM.')
        await fenrir.send_message(invokerid, message.chat.title + ': ' + chatlink)

    @group_only
    @admin_only
    async def genlink(message: types.Message):
        chatlink = await message.chat.export_invite_link()
        invokerid = message.from_user.id
        await message.reply('Order received. Check your PM.')
        await fenrir.send_message(invokerid, message.chat.title + ': ' + chatlink)

    # async def getuserinfofromdb(message: types.Message):
    #     SQL = 'SELECT * FROM tguser WHERE id = %s'
    #     userid = int(float(message.get_args()))
    #     db_curs.execute(SQL, (userid,))
    #     user = db_curs.fetchone()
    #     display_user_from_db(user)

    @owner_only
    async def addusertodb(message_ori: types.Message):
        if message_ori.from_user.id == 404176080:
            message = message_ori.reply_to_message

            SQL = '''INSERT INTO tguser
                        (id, is_bot, first_name, last_name,
                         username, language_code)
                     VALUES (%s, %s, %s, %s, %s, %s)
                     ON CONFLICT (id) DO UPDATE 
                        SET is_bot = %s,
                            first_name = %s,
                            last_name = %s,
                            username = %s,
                            language_code = %s
                     ;'''

            userid = message.from_user.id
            is_bot = message.from_user.is_bot
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            username = message.from_user.username
            language_code = message.from_user.language_code

            print('>>>>>>>>>>>>>>>>>>>> DBADD     <<<<<<<<<<<<<<<<<<<<')
            print('user.id    :', userid)
            print('user.isbot :', is_bot)
            print('user.first :', first_name)
            print('user.last  :', last_name)
            print('user.uname :', username)
            print('user.lang  :', language_code)
            print('>>>>>>>>>>>>>>>>>>>> DBADD END <<<<<<<<<<<<<<<<<<<<\n')

            db_curs.execute(SQL, (userid, is_bot, first_name, last_name, username, language_code, is_bot, first_name, last_name, username, language_code))
            db_conn.commit()

            # await CMD_handler.whatisthis(message)


    async def whatisthis(message: types.Message):
        print('>>>>>>>>>>>>>>>>>>>> REPLY MSG <<<<<<<<<<<<<<<<<<<<')
        display_info_msg(message.reply_to_message)

    @owner_only
    async def saygoodnight(message: types.Message):
        if message.from_user.id == 404176080:
            await fenrir.send_message(message.chat.id, "Goodnight, everyone!")



class MSG_handler(object):
    """docstring for MSG_handler"""
    def __init__(self, message: types.Message):
        super(MSG_handler, self).__init__()
        self.message = message

    async def owo(message:types.Message):
        # if message.from_user.id == 278199718:
        #     await message.reply('Shut up trash')
        # elif message.from_user.id == 334174254:
        #     await message.reply('Shut up slut')
        # elif message.from_user.id == config.bot_owner:
        #     await message.reply('UwU nyaaa owner!')
        # else:
        #     await message.reply('What\'s this?')


        userid = message.from_user.id
        SQL = '''SELECT reply FROM oworep
                    WHERE
                     CASE
                        WHEN %s in (select foruserid from oworep)
                        THEN foruserid = %s
                     ELSE
                        foruserid = 0
                     END
              ;'''

        db_curs.execute(SQL, (userid, userid))
        replies = db_curs.fetchall()
        await message.reply(replies[random.randint(1, len(replies))-1][0])


        
def display_info_msg(message: types.Message):
    print('>>>>>>>>>>>>>>>>>>>> MSG START <<<<<<<<<<<<<<<<<<<<')
    print('msg_id:', message.message_id)
    print('')
    print('msg.fromuser.id    :', message.from_user.id)
    print('msg.fromuser.isbot :', message.from_user.is_bot)
    print('msg.fromuser.first :', message.from_user.first_name)
    print('msg.fromuser.last  :', message.from_user.last_name)
    print('msg.fromuser.uname :', message.from_user.username)
    print('msg.fromuser.lang  :', message.from_user.language_code)
    print('')
    print('msg.chat.id       :', message.chat.id)              #integer
    print('msg.chat.type     :', message.chat.type)          #string
    print('msg.chat.title    :', message.chat.title)        #chat title
    print('msg.chat.username :', message.chat.username)  #chat username
    print('')
    print('msg.date:', message.date)
    print('msg.text:', message.text)
    print('>>>>>>>>>>>>>>>>>>>>   MSG END <<<<<<<<<<<<<<<<<<<<\n')

def display_info_cmd(message: types.Message):
    print('>>>>>>>>>>>>>>>>>>>> CMD START <<<<<<<<<<<<<<<<<<<<')
    print('msg_id:', message.message_id)
    print('')
    print('msg.fromuser.id    :', message.from_user.id)
    print('msg.fromuser.isbot :', message.from_user.is_bot)
    print('msg.fromuser.first :', message.from_user.first_name)
    print('msg.fromuser.last  :', message.from_user.last_name)
    print('msg.fromuser.uname :', message.from_user.username)
    print('msg.fromuser.lang  :', message.from_user.language_code)
    print('')
    print('msg.chat.id       :', message.chat.id)              #integer
    print('msg.chat.type     :', message.chat.type)          #string
    print('msg.chat.title    :', message.chat.title)        #chat title
    print('msg.chat.username :', message.chat.username)  #chat username
    print('')
    print('msg.iscmd  :', message.is_command())
    print('msg.cmdarg :', message.get_full_command())
    print('msg.cmd    :', message.get_command())
    print('msg.arg    :', message.get_args())
    print('msg.date:', message.date)
    print('msg.text:', message.text)
    print('>>>>>>>>>>>>>>>>>>>>   CMD END <<<<<<<<<<<<<<<<<<<<\n')

def display_user_from_db(user):
    print('>>>>>>>>>>>>>>>>>>>> USR START <<<<<<<<<<<<<<<<<<<<')
    print('user.id    :', user[0])
    print('user.isbot :', user[1])
    print('user.first :', user[2])
    print('user.last  :', user[3])
    print('user.uname :', user[4])
    print('user.lang  :', user[5])
    print('>>>>>>>>>>>>>>>>>>>>   USR END <<<<<<<<<<<<<<<<<<<<\n')

def display_info_photo(message: types.Message):
    print('>>>>>>>>>>>>>>>>>>>> PHT START <<<<<<<<<<<<<<<<<<<<')
    print('msg_id:', message.message_id)
    print('')
    print('msg.fromuser.id    :', message.from_user.id)
    print('msg.fromuser.isbot :', message.from_user.is_bot)
    print('msg.fromuser.first :', message.from_user.first_name)
    print('msg.fromuser.last  :', message.from_user.last_name)
    print('msg.fromuser.uname :', message.from_user.username)
    print('msg.fromuser.lang  :', message.from_user.language_code)
    print('')
    print('msg.chat.id       :', message.chat.id)              #integer
    print('msg.chat.type     :', message.chat.type)          #string
    print('msg.chat.title    :', message.chat.title)        #chat title
    print('msg.chat.username :', message.chat.username)  #chat username
    for pht in message.photo:
        print('')
        print('pht.id       :', pht.file_id)     #string
        print('pht.width    :', pht.width)    #integer
        print('pht.height   :', pht.height)  #integer
        print('pht.filesize :', pht.file_size)     #integer
    print('>>>>>>>>>>>>>>>>>>>>   PHT END <<<<<<<<<<<<<<<<<<<<\n')



@fenrir_disp.message_handler(content_types = types.message.ContentType.TEXT)
async def cmd_msg_handler(message: types.Message):
    # if message.chat.id in config.bot_ban:
    #     return
    if message.chat.id not in config.bot_bind:
        return
    if(message.is_command()):
        command = message.get_command()[1:].lower()
        if(command.find('@') == -1):
            is_forbot = True
        elif(command[command.find('@')+1:] ==  fenrir_username.lower()):
            is_forbot = True
            command = command[0:command.find('@')]
        else:
            is_forbot = False

        if(is_forbot):
            display_info_cmd(message)
            await getattr(CMD_handler, command)(message)
            # try:
            #     await getattr(CMD_handler, command)(message)
            # except:
            #     pass
    else:
        display_info_msg(message)
        txt = message.text.lower()
        await getattr(MSG_handler, txt)(message)
        # try:
        #     txt = message.text.lower()
        #     await getattr(MSG_handler, txt)
        # except:
        #     pass

@fenrir_disp.message_handler(content_types = types.message.ContentType.PHOTO | types.message.ContentType.DOCUMENT)
async def photo_handler(message: types.Message):
    display_info_photo(message)

@group_only
@fenrir_disp.message_handler(content_types = types.message.ContentType.NEW_CHAT_MEMBERS | types.message.ContentType.LEFT_CHAT_MEMBER)
async def greeter_handler(message: types.Message):
    new_chat_users = message.new_chat_members
    # if message.chat.id == -254633737: #group testing
    if new_chat_users != []:
        new_chat_usernames = ''
        newct = 0
        for new_chat_user in new_chat_users:
            # if not new_chat_user.is_bot:
                new_chat_usernames = new_chat_usernames + ' @' + new_chat_user.username
                newct = newct + 1
        if new_chat_usernames != '':
            welcome_text = f'Hi there, {new_chat_usernames}! Welcome to {message.chat.title}.\nEnjoy your stay';
            await fenrir.send_message(message.chat.id, welcome_text)

    left_chat_user = message.left_chat_member
    # if message.chat.id == -254633737:   #group testing
    if left_chat_user != None:
        goodbye_text = f'So long, @{left_chat_user.username}! We\'ll probably miss you!'
        await fenrir.send_message(message.chat.id, goodbye_text)




#////////////////////////////////////////////////#
#////////////////////////////////////////////////#



if __name__ == '__main__':
    executor.start_polling(fenrir_disp, loop=loop)


    # Also you can use another execution method
    # try:
    #     loop.run_until_complete(main())
    # except KeyboardInterrupt:
    #     loop.stop()