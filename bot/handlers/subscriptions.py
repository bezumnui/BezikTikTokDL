from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.types import Message

from ..filters import GroupAdmin
from ..subscriptions import SubscriptionStore

router = Router(name="subscriptions")

_GROUPS = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})


@router.message(Command("sub", "unsub"), ~_GROUPS)
async def groups_only(message: Message) -> None:
    await message.reply("Subscriptions work in groups. Add me to a group and send /sub there.")


@router.message(Command("sub"), _GROUPS, GroupAdmin())
async def subscribe(message: Message, bot: Bot, subscriptions: SubscriptionStore) -> None:
    added = subscriptions.add(message.chat.id, message.chat.title or str(message.chat.id))
    text = ("Subscribed. I'll download every TikTok link posted here." if added
            else "This group is already subscribed.")
    if not await _sees_all_messages(message, bot):
        text += (
            "\n\n⚠️ I can't read regular messages here yet. Make me an admin, or disable privacy mode "
            "in @BotFather (/setprivacy → Disable) and re-add me to the group."
        )
    await message.reply(text)


@router.message(Command("unsub"), _GROUPS, GroupAdmin())
async def unsubscribe(message: Message, subscriptions: SubscriptionStore) -> None:
    if subscriptions.remove(message.chat.id):
        await message.reply("Unsubscribed. I'll only download links when asked with /dl or a mention.")
    else:
        await message.reply("This group isn't subscribed.")


@router.message(Command("sub", "unsub"), _GROUPS)
async def admins_only(message: Message) -> None:
    await message.reply("Only group admins can change the subscription.")


async def _sees_all_messages(message: Message, bot: Bot) -> bool:
    me = await bot.me()
    if me.can_read_all_group_messages:
        return True
    member = await bot.get_chat_member(message.chat.id, me.id)
    return member.status == ChatMemberStatus.ADMINISTRATOR
