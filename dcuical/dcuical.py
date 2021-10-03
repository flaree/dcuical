import aiohttp
import json

import icalendar
import datetime
import discord

from io import BytesIO

from redbot.core import commands
from redbot.core.data_manager import bundled_data_path, cog_data_path

ReqHeaders = {
    "Authorization": "basic T64Mdy7m[",
    "Content-Type" : "application/json; charset=utf-8",
    "credentials": "include",
    "Referer" : "https://opentimetable.dcu.ie/",
    "Origin" : "https://opentimetable.dcu.ie/"
}


class DCUICal(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.req_data = self.get_req_data()

    def get_req_data(self):
        with open(bundled_data_path(self) / "request.json") as f:
            return json.load(f)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())


    @commands.command(aliases=["ics"])
    async def ical(self, ctx, course: str, *ignored_modules: str):
        """
        Return an ICAL/ICS file for a DCU course timetable.
        """
        async with ctx.typing():
            async with self.session.post(f"https://opentimetable.dcu.ie/broker/api/CategoryTypes/241e4d36-60e0-49f8-b27e-99416745d98d/Categories/Filter?pageNumber=1&query={course}", headers=ReqHeaders) as req:
                if req.status != 200:
                    await ctx.send("Course not found.")
                    return
                data = (await req.json())['Results'][0]['Identity']
            self.req_data['CategoryIdentities'][0] = data

            async with self.session.post(f"https://opentimetable.dcu.ie/broker/api/categoryTypes/241e4d36-60e0-49f8-b27e-99416745d98d/categories/events/filter", headers=ReqHeaders, json=self.req_data) as req:
                if req.status != 200:
                    await ctx.send("Course timetable not found.")
                    return
                timetable = await req.json()
            cal = icalendar.Calendar()

            for event_obj in timetable[0]["CategoryEvents"]:
                event = icalendar.Event()
                if any(ext.lower() in event_obj['ExtraProperties'][0]['Value'].lower() for ext in ignored_modules):
                    continue
                start = datetime.datetime.fromisoformat(event_obj["StartDateTime"])
                end = datetime.datetime.fromisoformat(event_obj["EndDateTime"])
                duration = (end - start)
                event.add("summary", f"{event_obj['ExtraProperties'][0]['Value']}")
                event.add("dtstart", start)
                event.add("dtend", end)
                event.add("duration", duration)
                event.add("location", f"{event_obj['Location']} {event_obj['EventType'] if event_obj['EventType'] != 'On Campus' else ''}")
                event.add("description", f"{event_obj['ExtraProperties'][1]['Value']}")
                cal.add_component(event)
            data = BytesIO(cal.to_ical())
            data.name = "file.ics"
            file = discord.File(data, filename=f"{course}.ics")

        await ctx.send(file=file)


        