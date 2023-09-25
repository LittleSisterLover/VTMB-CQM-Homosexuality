import __main__
import events
from random import Random
from random import randint
from time import time
from string import atoi
from zvtool.zvtool import *
import achievements
import dialogutil
import posters

import cqm_shortcut
import cqm_malkfun
import cqm_malkavian
import cqm_fuhack
import diablorie

from __main__ import Character

huntersDead = [0, 0, 0]

Find = __main__.FindEntityByName
FindList = __main__.FindEntitiesByName
FindClass = __main__.FindEntitiesByClass


##############################################################################
# Companion Mod
#
# The following events/methods were created to support the companion mod, but
# have been broken out globally so that other mods can hook into the extended
# events.

import configutil
import companion
import possessutil
import characterext
import dialogutil
import havenutil
import consoleutil
import fileutil
import eventutil
import statutil
import musicutil
import soundutil
from logutil import log

##############################################################################
# ZVTools
#

_mod_options=configutil.Options("mods.cfg")
if _mod_options.get("mod_enable_zvtools",0):
    from zvtool.zvtool import *

##############################################################################
# Root Events
##############################################################################

# OnPollEvent : Required logic_timer entities placed on every map.
# {
# "classname" "logic_timer"
# "StartDisabled" "0"
# "UseRandomTime" "0"
# "RefireTime" "15.0"
# "OnTimer" ",,,0,-1,OnPollEvent(),"
# "origin" "-2420.54 -2558.76 -111.97"
# }
#
# Polls every 15 seconds. 
def OnPollEvent():
    companion.timer_OnTimer()
    possessutil.timer_OnTimer()
    

# OnEnterMap : Required logic_auto entities placed on every map.
# {
# "classname" "logic_auto"
# "spawnflags" "0"
# "OnMapLoad" ",,,0,-1,OnEnterMap('sm_hub_1'),"
# "origin" "-2420.54 -2558.76 -111.97"
# }
# Notes : Does not get called on save game reload.
#         See OnBeginNormalMusic below to place
#         code you want executed on both map
#         transitions AND save game reloads. 

CompModIgnoreMaps=("la_malkavian_1","sp_tutorial_1","sp_ninesintro","sp_theatre" \
                  ,"sp_taxiride","sp_masquerade_1","sp_epilogue")

def OnEnterMap(mapName):
    global InCombat
    
    ## 
    # Fixing random bug on this map where player will fly off the map completely
    ##
    if(mapName=="ch_cloud_1"):
        __main__.FindPlayer().SetOrigin((0, 85, 9))
    
    cqm_shortcut.lostTrail(mapName)
    
    __main__.G.currentMap=mapName
    log("Entering map [%s]" % mapName,1)
    log("Game State [%d]" % __main__.G.Story_State,1)

    # Buf fix Patch 1.2: PC changes maps during combat. OnBeginNormal Music
    # fires. InCombat state was still 1, so OnEndCombat also fired, respawning
    # any companions standing on the map that hadn't been cleaned up yet. This
    # in turn re-added them to the G.henchmen array and caused a doopleganger to
    # appear when populateCompanions was finally invoked. Resetting InCombat
    # to 0 prevents the bug.
    InCombat=0

    # Skip Tutorial Bug Fix
    if "sm_pawnshop_1" == mapName:
        if not __main__.FindPlayer().HasItem("item_g_lockpick"):
            __main__.FindPlayer().GiveItem("item_g_lockpick")
    
    # Fix Edited Map bug
    try:
        world=__main__.FindEntitiesByName("world")[0]
        world.AIEnable(1)
    except:
        pass

    # Cycles Maps Support
    if __main__.G.cyclemaps:
        index = statutil.MapNames.index(mapName) + 1
        if index < len(statutil.MapNames):
            nextTask="consoleutil.console(\"map %s\")" % statutil.MapNames[index]
            __main__.ScheduleTask(7.0,nextTask)
        else:
            __main__.G.cyclemaps=0

    # Initialize modules (1 time per campaign)
    if not __main__.G.vamputilinit:
        InitializeModules()

    # Music Manager Integration
    musicutil.OnEnterMap(mapName)

    # Sound Manager (Battle Cries)
    soundutil.OnEnterMap(mapName)

    # Damsel Fight Setup
    if 1==__main__.G.Damsel_Fight and mapName == "la_hub_1":
        damsel = __main__.FindEntityByName("Damsel")
        if damsel:
            __main__.G.Damsel_Fight=2
            damsel.ScriptUnhide()

    if 2==__main__.G.Damsel_Fight and mapName == "la_expipe_1":
        damsel = __main__.FindEntityByName("Damsel")
        if damsel:
            log("Hiding original Damsel. Renaming to Damsel_orig")
            damsel.SetName("Damsel_orig")
            damsel.ScriptHide()
            __main__.G.Damsel_Fight=3

    if not (mapName in CompModIgnoreMaps):
        companion.auto_OnMapLoad(mapName)
        possessutil.auto_OnMapLoad(mapName)

    # Pose System Fixes
    __main__.ccmd.fixcamera=""
    if __main__.G.poseKeysMapped: havenutil.UnmapPoseKeys()

    if havenutil.isInHaven():
        log("Calling havenutil.OnMapLoad",1)
        havenutil.OnMapLoad(mapName)

    # Create Phylax Spell Easter Egg
    if mapName == "la_malkavian_2":
        if 0 == __main__.G._spawned_spell:
            spell=__main__.CreateEntityNoSpawn("item_p_occult_hacking", (509.03125, 688.03125, -3007.96875),(0,0,0))
            if spell:
                __main__.CallEntitySpawn(spell)
            if spell:
                __main__.G._spawned_spell=1
    

# The following methods require an events_world object
# added/updated on every map that key into the
# OnCombatMusicStart/OnNormalMusicStart events
# {
# "classname" "events_world"
# "targetname" "world"
# "StartHidden" "0"
# "OnCombatMusicStart" ",,,0,-1,OnBeginCombatMusic(),"
# "OnNormalMusicStart" ",,,0,-1,OnEndCombatMusic(),"
# "origin" "-2683.47 -2152.89 -111"
# }

InCombat=0
def OnBeginCombatMusic():
    global InCombat

    log("OnBeginCombatMusic")
    InCombat=1

    # Music Manager Integration
    musicutil.OnBeginCombatMusic()
    # Sound Manager Integration (Battle Cries)
    soundutil.OnBeginCombatMusic()
    

    OnBeginCombat()

def OnBeginNormalMusic():
    global InCombat

    log("OnBeginNormalMusic")

    # Music Manager Integration
    musicutil.OnBeginNormalMusic()
    # Sound Manager Integration (Battle Cries)
    soundutil.OnBeginNormalMusic()

    if InCombat:
        InCombat=0
        OnEndCombat()
    else:
        log("Map Load Detected")
#        if not __main__.FindPlayer().IsPC():
#            consoleutil.console("vamplight_enabled 1");
        # if havenutil.isInHaven():
        #    log("Calling havenutil.OnMapLoad",1)
        #    havenutil.OnMapLoad(__main__.G.currentMap)
        
def OnEndNormalMusic():
    log("Calling OnEndNormalMusic")


# The following methods require an events_player object
# added/updated on every map that key into the
# OnPlayerTookDamage/OnPlayerKilled/OnWolfMorphBegin
# OnWolfMorphEnd events
# {
# "classname" "events_player"
# "StartHidden" "0"
# "enabled" "1"
# "targetname" "pevents"
# "OnWolfMorphBegin" ",,,0,-1,possessutil.player_OnWolfMorphBegin(),"
# "OnWolfMorphEnd" ",,,0,-1,possessutil.player_OnWolfMorphEnd(),"
# "OnPlayerTookDamage" ",,,0,-1,possessutil.player_OnPlayerTookDamage(),"
# "OnPlayerKilled" ",,,0,-1,possessutil.player_OnPlayerKilled(),"
# "origin" "-2683.47 -2152.89 -111"
# }

def OnBeginWolfMorph():
    log("OnBeginWolfMorph")

def OnEndWolfMorph():
    log("OnEndWolfMorph")

def OnPlayerDamaged():
    log("OnPlayerDamaged")
    possessutil.player_OnPlayerTookDamage()

def OnPlayerDeath():
    log("OnPlayerDeath")
    possessutil.player_OnPlayerKilled()

# OnBeginDialog requires adding a call to this function to every dialog in the game.
# Return value of 1 cancels dialog. (If this functional always returned 1,
# you wouldn't be able to speak to anyone in the game).

def OnBeginDialog(pc,npc,dialogindex):
    # Music Manager Integration
    musicutil.OnBeginDialog()

    log("Starting Dialog with [%s] dialog index [%d]" % (npc.GetName(),dialogindex))
    ret = companion.storeGlobals(npc)
    ret = (ret or possessutil.handleDialogIndex(pc,npc,dialogindex))
    if 1 != ret: companion.handleBeginDialog(dialogindex)
    return ret

        

##############################################################################
# Derived Events
##############################################################################

# InitializeModules:
#   __main__.G is not valid when vamputils loads. By keying
#   into the OnEnterMap event, we delay module initialization
#   until __main__.G is valid. Note: this will only get
#   called once, when a player begins a new game. 

def InitializeModules():
    __main__.G.vamputilinit=1
    # compmodVersion variable introduced with version 1.2
    # will allow autopatching code to be installed to help
    # mitigate issues with loading old save games. 
    __main__.G.compmodVersion=1.21
    __main__.G._pcinfo={}
    storePCInfoOnce()
    companion.initCompanion()
    possessutil.initPossessUtil()
    havenutil.initHavenUtil()
    
def OnBeginCombat():

    log("OnBeginCombat")
    companion.OnCombatStart()
    possessutil.OnCombatStart()

def OnEndCombat():
    log("OnEndCombat")
    companion.OnCombatEnd()
    possessutil.OnCombatEnd()



##############################################################################
# DEVELOPMENT UTILITIES
##############################################################################


#
# LimitSet is a convenience function for dialogs. See Mod Developers
# Guide for use
#
def LimitSet(iteration,setid):
    npc = None
    modelindex = -1
    timestalked = -1
    oldTT = -1
    oldMI = -1
    oldID = -1
    oldIter = 512    
    try:
        npc = __main__.npc
        modelindex = npc.modelindex
        timestalked = npc.times_talked
    except:
        npc = __main__.FindPlayer()
    try:
        oldTT   = npc.limitset_timestalked
        oldMI   = npc.limitset_modelindex
        oldID   = npc.limitset_id
        oldIter = npc.limitset_iteration
    except:
        pass
    if (timestalked != oldTT) or (modelindex != oldMI) or (setid != oldID) or not (iteration > oldIter):
        npc.limitset_timestalked=timestalked
        npc.limitset_modelindex=modelindex
        npc.limitset_iteration=iteration
        npc.limitset_id=setid
        return 1
    return 0
        
#
# Start New Game, from Tutorial lwvwl, bring up console window and type
# cycleMaps() <- Auto visits every map in the game, generating the
#                map nodes so that you dont get AI disabled errors.
def cycleMaps(begin=0):
    __main__.G.cyclemaps=1
    start="noclip\nnotarget\ngod\nmap %s" % statutil.MapNames[begin]
    consoleutil.console(start)

_debugToggle=1
def debugMode():
    global _debugToggle
    """ Convenience function for exploring maps, especially otherwise hostile areas.
    param 1 : toggle. [0/1]. (def=1)"""
    if (_debugToggle):
        _debugToggle=0
        __main__.cvar.draw_hud=0
        __main__.cvar.cl_showfps=1
        __main__.cvar.cl_showpos="1"
    else:
        __main__.cvar.draw_hud=1
        __main__.cvar.cl_showfps=0
        __main__.cvar.cl_showpos="0"
    __main__.ccmd.notarget=""
    __main__.ccmd.noclip=""
    __main__.ccmd.picker=""
    __main__.ccmd.ai_show_interesting=""


def showInstances(prefix="npc_V"):
    """ Similar to the console command report_entities, however this function will tell you entity names

    param 1 : prefix. String filter. Only classes starting with filter are returned. (def="npc_V")"""

    entities = __main__.FindEntitiesByClass(prefix+"*")
    print "Class                                  Name"
    print "---------------------------------------------------------"
    for ent in entities:
      name="";
      try: name=ent.GetName()
      except: pass
      if name != "":
        print "%s %s" % (ent.classname.ljust(35),ent.GetName())


#
# This is also called when the game begins to ensure the _pcinfo array is initialized for the Embrace
# capability (We need to know what the original clan and disciplines were).

# Takes a snapshot of the PC and stores it in globally accessible array "__main__.G._pcinfo".
# Tis version gets called once per game, so we can set some values that should
# never change over the coarse of the game. 
def storePCInfoOnce():
    pc = __main__.FindPlayer()
    if pc.IsPC():
        i = 0
        while i < len(statutil.AttributeNames):
            __main__.G._pcinfo[statutil.AttributeNames[i]]=getattr(pc,"base_" + statutil.AttributeNames[i])
            i+=1
        i = 0
        while i < len(statutil.AbilityNames):
            __main__.G._pcinfo[statutil.AbilityNames[i]]=getattr(pc,"base_" + statutil.AbilityNames[i])
            i+=1
        i = 0
        while i < len(statutil.DisciplineNames):
            __main__.G._pcinfo[statutil.DisciplineNames[i]]=getattr(pc,"base_" + statutil.DisciplineNames[i])
            i+=1
        __main__.G._pcinfo["armor"]=pc.armor_rating
        __main__.G._pcinfo["masquerade"]=pc.base_masquerade
        __main__.G._pcinfo["model"]=pc.model
        __main__.G._pcinfo["experience"]=pc.base_experience
        __main__.G._pcinfo["bloodpool"]=pc.base_bloodpool
        __main__.G._pcinfo["humanity"]=pc.base_humanity

        # One time storage:
        __main__.G._pcinfo["vhistory"]=pc.vhistory
        __main__.G._pcinfo["name"]=__main__.cvar.name    
        __main__.G._pcinfo["clan"]=pc.clan

# Takes a snapshot of the PC and stores it in globally accessible array "__main__.G._pcinfo".
# Possession calls this function when the PC possesses someone to ensure the info is up to date
# so that XP re-embursment can be properly calculated when the PC unpossesses.
def storePCInfo():
    pc = __main__.FindPlayer()
    if pc.IsPC():
        i = 0
        while i < len(statutil.AttributeNames):
            __main__.G._pcinfo[statutil.AttributeNames[i]]=getattr(pc,"base_" + statutil.AttributeNames[i])
            i+=1
        i = 0
        while i < len(statutil.AbilityNames):
            __main__.G._pcinfo[statutil.AbilityNames[i]]=getattr(pc,"base_" + statutil.AbilityNames[i])
            i+=1
        i = 0
        while i < len(statutil.DisciplineNames):
            __main__.G._pcinfo[statutil.DisciplineNames[i]]=getattr(pc,"base_" + statutil.DisciplineNames[i])
            i+=1
        __main__.G._pcinfo["armor"]=pc.armor_rating
        __main__.G._pcinfo["masquerade"]=pc.base_masquerade
        __main__.G._pcinfo["model"]=pc.model
        __main__.G._pcinfo["experience"]=pc.base_experience
        __main__.G._pcinfo["bloodpool"]=pc.base_bloodpool
        __main__.G._pcinfo["humanity"]=pc.base_humanity




##############################################################################
# Unofficial Patch Functions
##############################################################################

#Switching between Basic and Plus patch, added by wesp

def setBasic():
    print "Unofficial Patch 9.2 Basic"
    G  = __main__.G
    G.Patch_Plus = 0
    __main__.ccmd.detailfade=""
    __main__.ccmd.detaildist=""
    pc = __main__.FindPlayer()
    if not (pc.HasItem("item_w_fists")):
        pc.GiveItem("item_w_fists")
        pc.GiveItem("weapon_physcannon")
        pc.GiveItem("item_g_wallet")
        pc.GiveItem("item_g_keyring")
        pc.GiveItem("item_a_lt_cloth")
    if G.Patch_Plus == 0:
        Find("idle_timer").Disable()
        axe = __main__.Find("wesp_axe")
        if axe: axe.ScriptUnhide()
        if axe: axe.Kill()
        axenode = __main__.Find("wesp_axenode")
        if axenode: axenode.ScriptUnhide()
        if axenode: axenode.Kill()
        blade = __main__.Find("wesp_blade")
        if blade: blade.Kill()
        bladenode = __main__.Find("wesp_bladenode")
        if bladenode: bladenode.Kill()

def setPlus():
    G  = __main__.G
    G.PP = 1
    G.Patch_Plus = 1
    G.Jack_Extra = 1
    G.Flynn_Extra = 1
    G.Extra_Lines = 1
    G.Linux_Wine = 1
    __main__.ccmd.detailfade=""
    __main__.ccmd.detaildist=""
    __main__.ccmd.clothes=""
    pc = __main__.FindPlayer()
    if not (pc.HasItem("item_w_fists")):
        pc.GiveItem("item_w_fists")
        pc.GiveItem("weapon_physcannon")
        pc.GiveItem("item_g_wallet")
        pc.GiveItem("item_g_keyring")
        pc.GiveItem("item_a_lt_cloth")
    if G.Patch_Plus == 1:
        plus = __main__.FindEntitiesByName("plus_*")
        for p in plus:
            p.ScriptUnhide()
        basic = __main__.FindEntitiesByName("basic_*")
        for b in basic:
            b.ScriptHide()
        cop = Find("Cop_Deck1_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck3_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck2_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck4_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck5_Guard")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck6_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck4_Guard2")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        cop = Find("Cop_Deck4_Guard3")
        if cop: cop.SetModel("models/character/npc/common/Cop_Variant/rookied_cop/Rookied_Cop.mdl")
        tong = Find("tong_sidekick_1")
        if tong: tong.SetModel("models/character/npc/unique/Chinatown/Tong_Leader/Tong_Leader.mdl")
        tong = Find("Tong_Floor2_Patrol")
        if tong: tong.SetModel("models/character/npc/unique/Chinatown/Tong_Leader/Tong_Leader.mdl")
        lasombra = Find("LaSombra")
        if lasombra: lasombra.SetModel("models/character/npc/common/doppleganger/doppleganger_female.mdl")
        lasombra = Find("LaSombra_2")
        if lasombra: lasombra.SetModel("models/character/npc/common/doppleganger/doppleganger_female.mdl")
        lasombra = Find("LaSombra_3")
        if lasombra: lasombra.SetModel("models/character/npc/common/doppleganger/doppleganger_female.mdl")
        shovel = Find("f2_m_potence_1")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        shovel = Find("f2_m_potence_2")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        shovel = Find("f1_m_potence_1")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        shovel = Find("f1_m_potence_2")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        shovel = Find("f3_m_potence_1")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        shovel = Find("f3_m_potence")
        if shovel: shovel.SetModel("models/character/npc/common/Shovelhead/shovelhead_short.mdl")
        nines = Find("Nines")
        if (G.Story_State == 115 and nines): nines.SetModel("models/character/npc/unique/Downtown/Nines/Nines_damagedw.mdl")
        flunky3 = Find("flunky3")
        if flunky3: flunky3.SetModel("models/character/npc/unique/Downtown/Skelter/Skelter.mdl")
        flunky4 = Find("flunky4")
        if flunky4 and (IsClan(pc,"Brujah")): flunky4.SetModel("models/character/pc/male/toreador/armor0/Toreador_Male_Armor_0.mdl")
        flunky5 = Find("flunky5")
        if flunky5 and (IsDead("Sweeper")):
            if (IsClan(pc,"Toreador")): flunky5.SetModel("models/character/pc/male/gangrel/armor_1/Gangrel_Male_Armor_1.mdl")
            else: flunky5.SetModel("models/character/pc/male/toreador/armor1/Toreador_Male_Armor_1.mdl")
        flunky6 = Find("flunky6")
        if (flunky6 and G.Copper_Nines == 0):
            if (IsClan(pc,"Brujah")): flunky6.SetModel("models/character/pc/male/gangrel/armor_1/Gangrel_Male_Armor_1.mdl")
            else: flunky6.SetModel("models/character/pc/male/brujah/armor1/Brujah_Male_Armor_1.mdl")
        flunky7 = Find("flunky7")
        if (flunky7 and G.Killer_Nines == 0):
            if (IsClan(pc,"Malkavian")): flunky7.SetModel("models/character/pc/male/gangrel/armor_1/Gangrel_Male_Armor_1.mdl")
            else: flunky7.SetModel("models/character/pc/male/malkavian/armor1/Malkavian_Male_Armor_1.mdl")
        flunky8 = Find("flunky8")
        if flunky8 and (IsClan(pc,"Toreador") and not pc.IsMale()): flunky8.SetModel("models/character/pc/female/brujah/armor0/Brujah_Female_Armor_0.mdl")
        gargoyleguard = Find("gargoyleguard")
        if (gargoyleguard and G.Gargoyle_Convinced == 0):
            gargoyleguard.ScriptHide()
        clothes = Find("plus_clothing")
        condoms = Find("plus_condoms")
        if clothes and G.Player_Homo == 1:
            gender = pc.IsMale()
            if gender: clothes.ScriptHide()
            else: condoms.ScriptHide()
        box = Find("plus_cigarbox")
        money = Find("basic_money")
        if box: box.AddEntityToContainer("basic_money")
        stumpy = Find("stumpy")
        if (stumpy and G.Gimble_Dead == 1):
            stumpy.ScriptHide()
        tub = Find("plus_tub")
        if (tub and (G.Killer_Hostile > 0 or G.Killer_Freed > 0)):
            junkteleport = Find("JunkyardTeleport2")
            junkteleport.ScriptHide()
            junkdoor = Find("jnkshkb")
            junkdoor.Unlock()
# I don't have this entity in CQM
# so just cancelling this unhide            
        asianvamp = Find("AsianVamp")
        if asianvamp and G.Asian_Swap == 0:
#            asianvamp.ScriptHide()
#            asianvamp.SetName("AsianVamp_basic")
#            asianvampplus = Find("AsianVamp_plus")
#            asianvampplus.ScriptUnhide()
#            asianvampplus.SetName("AsianVamp")
#            G.Asian_Swap = 1
            pass

        copperremains = Find("wesp_copper")
        copperstake = Find("wesp_stake") 
        if (copperremains and G.Copper_Prince == 1 and G.Copper_Seen == 0):
            copperremains.ScriptUnhide()
            copperstake.ScriptUnhide()
            G.Copper_Seen = 1
        elif (copperremains and G.Copper_Seen == 1):
            copperremains.Kill()
            copperstake.Kill()
        doll6 = Find("plus_Doll6")
        if doll6 and G.Doll6_Dead == 1:
            doll6.Kill()
        vendor = Find("Smoke_Vendor")
        if vendor and G.Vendor_Dead == 1:
            vendor.Kill()
        spotdoor = Find("redspotstorage")
        if spotdoor and G.Spot_Door == 0:
            knobs = __main__.FindEntitiesByName("dancer_door-doorknob")
            for knob in knobs:
                knob.Unlock()
            G.Spot_Door = 1
        locke = Find("Jezebel_Locke")
        if locke and G.Locke_Swap == 0:
#            locke.ScriptHide()
#            locke.SetName("Jezebel_Locke_basic")
#            lockeplus = Find("Jezebel_Locke_plus")
#            lockeplus.ScriptUnhide()
#            lockeplus.SetName("Jezebel_Locke")
#            G.Locke_Swap = 1
            pass
        bladebros = Find("ChangBrosBlade_plus")
        if bladebros and G.Chang_Swap == 0:
            bladebros.SetName("ChangBrosBlade")
            bladebrosbasic = Find("ChangBrosBlade_basic")
            bladebrosbasic.Kill()
            clawbros = Find("Chang_plus")
            clawbros.SetName("Chang")
            clawbrosbasic = Find("Chang_basic")
            clawbrosbasic.Kill()
            G.Chang_Swap = 1
        sarc = Find("sarc_plus")
        if sarc and G.Story_State >= 65:
            sarc.ScriptHide()
            sarcbasic = Find("sarc_basic")
            sarcbasic.ScriptHide()
        museummanhole = Find("Manhole_Museum")
        if museummanhole:
            museumcabbie = Find("cabbie")
            museumcabbie.WillTalk(0)
            doorfire = Find("door_fire")
            doorfire.Unlock()
            museumteleport = Find("museum_teleport")
            museumteleport.Enable()
            if G.Story_State >= 30:
                beckett = Find("Beckett")
                beckett.ScriptHide()
                if IsClan(pc,"Nosferatu"):
                    manholefake = Find("Manhole_Museum_Fake")
                    manhole = Find("Manhole_Museum")
                    manholefake.ScriptHide()
                    manhole.ScriptUnhide()
                else: museumcabbie.WillTalk(1)
        giovannimanhole = Find("Manhole_Giovanni")
        if giovannimanhole:
            giovannicabbie = Find("cabbie")
            giovannicabbie.WillTalk(0)
            if G.Story_State >= 65:
                if IsClan(pc,"Nosferatu"):
                    manholefake = Find("Manhole_Giovanni_Fake")
                    manhole = Find("Manhole_Giovanni")
                    manholefake.ScriptHide()
                    manhole.ScriptUnhide()
                else: giovannicabbie.WillTalk(1)
        shortcut = Find("shortcut_open")
        shortcut_off = Find("shortcut_closed")
        if G.Shortcut_Unlocked == 1:
            if shortcut: shortcut.ScriptUnhide()
            if shortcut_off: shortcut_off.ScriptHide()
        else:
            if shortcut: shortcut.ScriptHide()
            if shortcut_off: shortcut_off.ScriptUnhide()
        if G.Jumbles_Removed == 1 and G.LaSombra_Seen == 1 and G.Chinatown_Open == 1:
            G.Library_Ready = 1
        smokenote = Find("smoke_note")
        smokenotenode = Find("smoke_note_node")
        if G.Library_Smoke == 1:
            if smokenote: smokenote.ScriptUnhide()
            if smokenotenode: smokenotenode.ScriptUnhide()
        else:
            if smokenote: smokenote.ScriptHide()
            if smokenotenode: smokenotenode.ScriptHide()
        coffeedoor = Find("plus_coffee_door")
        if G.Library_Coffee > 0:
            if coffeedoor: coffeedoor.Unlock()
        else:
            if coffeedoor: coffeedoor.Lock()
        libraryopen = Find("library_open")
        libraryclosed = Find("library_closed")
        if G.Library_Open > 0:
            if libraryopen: libraryopen.ScriptUnhide()
            if libraryclosed: libraryclosed.ScriptHide()
        else:
            if libraryopen: libraryopen.ScriptHide()
            if libraryclosed: libraryclosed.ScriptUnhide()
        andrei = Find("Andrei")
        if ( andrei and G.Story_State == 35 ): 
            andrei.ScriptHide()

        watchman = Find("watchman")
        if (watchman and G.LaSombra_Seen == 0):
            Find("watchman").ScriptUnhide()
            __main__.ScheduleTask(2.0, "__main__.FindEntityByName(\"teleport_sequence\").BeginSequence()")
            G.LaSombra_Seen = 1
        plus = __main__.FindEntitiesByName("plus_ChangCoffin*")
        n = 1
        #print "renaming"
        for b in plus:
            b.SetName("ChangCoffin%d"%n)
            n = n+1
        basic = __main__.FindEntitiesByName("basic_ChangCoffin*")
        n = 1
        #print "renaming"
        for b in basic:
            b.SetName("ChangCoffin%d"%n)
            n = n+1
        if (__main__.IsClan(__main__.FindPlayer(), "Malkavian") and __main__.G.Stop_Shake == 0):
            __main__.G.Player_Malkavian = 1
            __main__.ccmd.ropeshake=""
        else:
            __main__.G.Stop_Shake = 0
            __main__.ccmd.ropestop=""
        events = __main__.FindEntityByName("events_player_plus")
        if events: events.EnableOutputs()
        #Changes v_thaumaturgy.mdl to match clan and gender, added by Entenschreck, changed by wesp
        pc = __main__.FindPlayer()
        gender = pc.IsMale()
        #copies Nosferatu version
        if IsClan(pc, "Nosferatu") and G.File_Copied_Nos == 0:
            print "Changing v_thaumaturgy.mdl to Nosferatu one"
            src = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view_nosferatu\\v_thaumaturgy.mdl"
            dst = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view\\v_thaumaturgy.mdl"
            fileutil.copyfile(src, dst)
            G.File_Copied_Nos = 1
            G.File_Copied_Male = 0
            G.File_Copied_Female = 0
        #copies male version
        elif gender and G.File_Copied_Male == 0:
            print "Changing v_thaumaturgy.mdl to male one"
            src = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view_male\\v_thaumaturgy.mdl"
            dst = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view\\v_thaumaturgy.mdl"
            fileutil.copyfile(src, dst)
            G.File_Copied_Nos = 0
            G.File_Copied_Male = 1
            G.File_Copied_Female = 0
        #copies female version
        elif not gender and G.File_Copied_Female == 0 and pc.clan == 7:
            print "Changing v_thaumaturgy.mdl to female one"
            src = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view_female\\v_thaumaturgy.mdl"
            dst = fileutil.getcwd() + "\\CQM\\models\\weapons\\thaumaturgy\\view\\v_thaumaturgy.mdl"
            fileutil.copyfile(src, dst)
            G.File_Copied_Nos = 0
            G.File_Copied_Male = 0
            G.File_Copied_Female = 1

def unhidePlus():
    c  = __main__.ccmd
    c.patchtype=""

#Particles for dialogue Domination and Presence, added by wesp
def dialogParticles():
    pc = __main__.FindPlayer()
    if IsClan(pc,"Tremere"):
        __main__.npc.SpawnTempParticle("dominate_particles")
    if IsClan(pc,"Brujah") or IsClan(pc,"Toreador"):
        __main__.npc.SpawnTempParticle("presence_particles")

#Humanity loss on killing civilians, added by wesp
def civilianDeath(override=0):
    pc = __main__.FindPlayer()
    if (pc.humanity >= 4 and (__main__.G.Patch_Plus == 1 or override==1)):
        ChangeHumanity( -1,3 )

#Masquerade violation for killing kindred in public, added by Malkav and wesp
def checkFieryDeath(name):
    masq = 0
    dist = 600      #normal vision range for open spaces
    p1 = Find(name).GetCenter()
    alleys = FindList("Trigger_Prostitut*") + FindList("jewbkdr")
    for alley in alleys:
        p2 = alley.GetCenter()
        if (distanceSquared(p1, p2) < 40000): dist = 150     #40000 -> 200 around trigger, 150 reduced visibility in alleys
    distsq = dist * dist
    guys = FindClass("npc_VCop") + FindClass("npc_VDialogPedestrian") + FindClass("npc_VPedestrian") + FindClass("npc_VHuman") + FindClass("npc_VHumanCombatant")
    for guy in guys:
        p2 = guy.GetCenter()
        if (distanceSquared(p1, p2) < distsq): masq = 1
    if (masq == 1 and __main__.G.Patch_Plus == 1): __main__.FindPlayer().ChangeMasqueradeLevel(1)

#Checking Research for occult items, added by wesp
def checkOccult():
    pc = __main__.FindPlayer()
    __main__.G.Player_Research = pc.CalcFeat("research")
    #print(__main__.G.Player_Research)
    if pc.HasItem("item_w_zombie_fists") and __main__.G.Player_Research >= 4:
        pc.RemoveItem("item_w_zombie_fists")
        pc.GiveItem("item_p_occult_passive_durations")
        print "Galdjum swapped"
    if pc.HasItem("item_w_werewolf_attacks") and __main__.G.Player_Research >= 6:
        pc.RemoveItem("item_w_werewolf_attacks")
        pc.GiveItem("item_p_occult_obfuscate")
        print "Zharalketh swapped"
    if pc.HasItem("item_w_tzimisce3_claw") and __main__.G.Player_Research >= 2:
        pc.RemoveItem("item_w_tzimisce3_claw")
        pc.GiveItem("item_p_occult_frenzy")
        print "Tarulfang swapped"
    if pc.HasItem("item_w_tzimisce_melee") and __main__.G.Player_Research >= 8:
        pc.RemoveItem("item_w_tzimisce_melee")
        pc.GiveItem("item_p_occult_experience")
        print "Saulocept swapped"
    if pc.HasItem("item_w_sabbatleader_attack") and __main__.G.Player_Research >= 8:
        pc.RemoveItem("item_w_sabbatleader_attack")
        pc.GiveItem("item_p_occult_hacking")
        print "Braid Talisman swapped"
    if pc.HasItem("item_w_manbat_claw") and __main__.G.Player_Research >= 2:
        pc.RemoveItem("item_w_manbat_claw")
        pc.GiveItem("item_p_occult_dodge")
        print "Weekapaug Thistle swapped"
    if pc.HasItem("item_w_hengeyokai_fist") and __main__.G.Player_Research >= 6:
        pc.RemoveItem("item_w_hengeyokai_fist")
        pc.GiveItem("item_p_occult_heal_rate")
        print "Mummywrap Fetish swapped"
    if pc.HasItem("item_w_gargoyle_fist") and __main__.G.Player_Research >= 4:
        pc.RemoveItem("item_w_gargoyle_fist")
        pc.GiveItem("item_p_occult_thaum_damage")
        print "Daimonori swapped"

#Player learns new Discipline, added by Entenschreck
def newDiscipline(x):
    c  = __main__.ccmd
    pc=__main__.FindPlayer()
    if x == 1:
        c.incAnimalism=""
    elif x == 2:
        c.incAuspex=""
    elif x == 3:
        c.incCelerity=""
    elif x == 4:
        c.incDementate=""
    elif x == 5:
        c.incDominate=""
    elif x == 6:
        c.incFortitude=""
    elif x == 7:
        c.incObfuscate=""
    elif x == 8:
        c.incPotence=""
    elif x == 9:
        c.incPresence=""
    elif x == 10:
        c.incProtean=""
    elif x == 11:
        c.incThaumaturgy=""    #should actually never get this
    c.showDiscipline=""

#609: Andrei intro for Tremere, added by EntenSchreck
def WhatIsThatSmell():
    pc = __main__.FindPlayer()
    clan = pc.clan
    if clan == 7:	#Tremere
        andrei = Find("plus_Andrei")
        andrei.PlayDialogFile("Character/dlg/hollywood/andrei/line5_col_e.mp3")

#609: Starts Dialog with Andrei while he's walking, added by EntenSchreck
def HelloYoungCainite():
    pc = __main__.FindPlayer()
    clan = pc.clan
    if clan == 7:	#Tremere
        andrei = Find("plus_Andrei")
        andrei.PlayDialogFile("Character/dlg/hollywood/andrei/line151_col_e.mp3")
    else:
        andrei = Find("plus_Andrei")
        andrei.PlayDialogFile("Character/dlg/hollywood/andrei/line11_col_e.mp3")

#CLINIC: Sets Heather quest states, added by wesp
def heatherQuest1():
    pc = __main__.FindPlayer()
    if __main__.G.Patch_Plus == 1:
        pc.SetQuest("Heather",1)
def heatherQuest2():
    pc = __main__.FindPlayer()
    if __main__.G.Patch_Plus == 1:
        pc.SetQuest("Heather",2)
def heatherQuest3():
    pc = __main__.FindPlayer()
    if __main__.G.Patch_Plus == 1:
        pc.SetQuest("Heather",3)

#CLINIC: Checks sneaking, added by wesp
def sneakTest():
    pc = __main__.FindPlayer()
    npc = __main__.Find("clinic_guard")
    pos1 = pc.GetOrigin()
    pos2 = npc.GetOrigin()
    if (__main__.G.Patch_Plus == 1 and ((pc.GetCenter()[2] - pc.GetOrigin()[2]) <= 18) and pc.CalcFeat("Sneaking") > 4 and distanceSquared(pos1, pos2) > 18000):
        return
    else:
        relay = __main__.Find("guard_warning")
        if(relay):
            relay.Trigger()

#CLINIC: Sets Heather quest, added by wesp
def heatherSetQuest():
    pc = __main__.FindPlayer()
    state = pc.GetQuestState("Heather")
    if (__main__.G.Patch_Plus == 1 and state == 1):
        __main__.G.Morgue_Heather = 1
        __main__.FindPlayer().SetQuest("Heather", 3)

#CLINIC: Updates Thin Blood quest, added by wesp
def freezerCode():
    pc = __main__.FindPlayer()
    if (__main__.G.Phil_Persuade == 0 and __main__.G.Phil_Drop == 0 and __main__.G.Phil_Code == 0):
        __main__.G.Phil_Code = 1
        pc.AwardExperience("Thinned05")

#CLINIC: Spawns Vandal blood pack, added by RobinHood70
def spawnVandalBlood():
    pc = __main__.FindPlayer()
    if (pc.AmmoCount("item_g_bluebloodpack") == 0):
        pc.GiveItem("item_g_bluebloodpack")
    elif (pc.AmmoCount("item_g_bluebloodpack") >= 10):
        vandal = Find("Vandal")
        center = vandal.GetCenter()
        point = (center[0], center[1], center[2] + 20)
        blood = __main__.CreateEntityNoSpawn("item_g_bluebloodpack", point, (0,0,0) )
        blood.SetName("vandal_blood")
        sparklies = __main__.CreateEntityNoSpawn("inspection_node", point, (0,0,0) )
        sparklies.SetParent("vandal_blood")
        __main__.CallEntitySpawn(blood)
        __main__.CallEntitySpawn(sparklies)
    else:
        pc.GiveAmmo("item_g_bluebloodpack",1)

#CLOUD: Chooses reward from Mr. Ox, added by wesp
def oxReward1():
    pc = __main__.FindPlayer()
    if __main__.G.Patch_Plus == 1:
        pc.GiveItem("item_p_occult_strength")
    else:
        pc.MoneyAdd(150)
def oxReward2():
    pc = __main__.FindPlayer()
    if __main__.G.Patch_Plus == 1:
        pc.GiveItem("item_p_occult_lockpicking")
    else:
        pc.MoneyAdd(250)

#DINER: talking to the thugs, added by wesp
def thugState():
    if (__main__.G.Thugs_Attack == 1):
        thug_1 = Find("assassin_e")
        thug_2 = Find("assassin_s")
        thug_3 = Find("assassin_w")
        thug_4 = Find("assassin_n")
        thug_1.SetRelationship("player D_HT 5")
        thug_2.SetRelationship("player D_HT 5")
        thug_3.SetRelationship("player D_HT 5")
        thug_4.SetRelationship("player D_HT 5")
    elif (__main__.G.Thugs_Peace == 1):
        thug_2 = Find("assassin_s")
        thug_2.WillTalk(0)
        trigger1 = Find("trigger_attack")
        trigger1.Disable()
        trigger2 = Find("go_attack")
        trigger2.Disable()
        __main__.thugsAllDead()

#DOWNTOWN: Get Beckett unstuck, added by wesp
def checkBeckettStuck():
    if (__main__.G.Beckett_Talk == 0):
        beckett = Find("Beckett")
        if beckett:
            org = __main__.FindPlayer().GetOrigin()
            rx = org[0] + 50
            beckett.SetOrigin((rx,org[1],org[2]))

#EMPIRE: Cardprinter, added by wesp
def cardPrinterEnablePlus():
    if (__main__.G.Hannah_Jezebel == 1 and __main__.G.Patch_Plus == 1):
        printer = Find("card_printer")
        printer.ScriptUnhide()

#EXHAUST PIPE: (un)Hide Nines gun, added by vladdmaster
def deagleNines():
    gun = Find("deagle")
    gun.ScriptUnhide()
    __main__.ScheduleTask(3.00, "__main__.Find(\"deagle\").ScriptHide()")

#GALLERY: Gives the player the money, added by wesp
def playerGotBox():
    pc = __main__.FindPlayer()
    if (__main__.G.Got_Cash == 0):
        __main__.G.Got_Cash = 1
        pc.MoneyAdd(250)
        box_spark = Find("box_sparklies")
        if box_spark: box_spark.ScriptHide()
        if (pc.humanity >= 6 and __main__.G.Charity_Know == 0):
            ChangeHumanity(-1,7)

#GIOVANNI MANSION 2: Feedback for killing Bruno, added by wesp
def brunoD():
    __main__.G.Bruno_Killed = 1
    pc = __main__.FindPlayer()
    if(__main__.G.Player_Sabbat==0):
        pc.SetQuest("Sarcophagus", 5)

#GIOVANNI MANSION 2: Spawns watch, added by Wesp5
def spawnWatch():
    pc = __main__.FindPlayer()
    if (pc.AmmoCount("item_g_watch_fancy") == 0):
        pc.GiveItem("item_g_watch_fancy")
    else:
        pc.GiveAmmo("item_g_watch_fancy",1)

#GIOVANNI MANSION 2: Spawns ring, added by Wesp5
def spawnGold():
    pc = __main__.FindPlayer()
    if (pc.AmmoCount("item_g_ring_gold") == 0):
        pc.GiveItem("item_g_ring_gold")
    else:
        pc.GiveAmmo("item_g_ring_gold",1)

#GIOVANNI MANSION 3: Keep door open, added by wesp
def changeLevelCheck():
    if (__main__.G.Nadia_Fright == 1 ):
        print ( "********* cleaning up *************" )
        door = Find("door_fake")
        door.ScriptHide()
        block = Find("door_block")
        block.ScriptHide()
        float = Find("Nadia_Motioning1")
        float.ScriptHide()
        float = Find("choreo_thisway")
        float.ScriptHide()
        float = Find("choreo_comon")
        float.ScriptHide()
        Nadia = Find("Nadia")
        Nadia.ScriptHide()
    else:
        door = Find("door_fake")
        door.ScriptUnhide()
        block = Find("door_block")
        block.ScriptUnhide()

#HALLOWBROOK HOTEL: Changes Models of the Spiderchicks, added by EntenSchreck
def MabelleneModel():
    M = Find("Mabellene I Hofteholder")
    M.SetModel("models/character/monster/tzimisce/creation1/creation1_full.mdl")
    Mcenter = M.GetOrigin()
    Mpoint = (Mcenter[0], Mcenter[1], Mcenter[2] + 20)
    M.SetOrigin(Mpoint)
def EvelynModel():
    E = Find("Evelyn")
    E.SetModel("models/character/monster/tzimisce/creation1/creation1_full.mdl")
    Ecenter = E.GetOrigin()
    Epoint = (Ecenter[0], Ecenter[1], Ecenter[2] + 20)
    E.SetOrigin(Epoint)

#HALLOWBROOK HOTEL: Changes firemage gender, added by wesp
def genderTremere():
    pc = __main__.FindPlayer()
    gender = pc.IsMale()
    clan = pc.clan
    mage = Find("Tremere_FireMage")
    female_mage = Find("Tremere_FireMage_Female")
    if (gender == 1 and clan == 7):
        female_mage.ScriptUnhide()
    else:
        mage.ScriptUnhide()

#HAVEN: Used to trigger library quest log, added by wesp
def librarySetQuest():
    print "Calling library set quest"
    pc = __main__.FindPlayer()
    if (__main__.G.Library_Smoke == 0):
        print "Setting state 1"
        pc.SetQuest("Library", 1)
        __main__.G.Library_Smoke = 1
    if (__main__.G.Library_Smoke == 2):
        pc.SetQuest("Library", 2)
        __main__.G.Library_Coffee = 1
        __main__.G.Library_Smoke = 3
    if (__main__.G.Library_Coffee == 2):
        pc.SetQuest("Library", 3)
        __main__.G.Library_Note = 1
        __main__.G.Library_Coffee = 3
    if (__main__.G.Library_Note == 2 and __main__.G.Library_Open == 0):
        pc.SetQuest("Library", 4)
        __main__.G.Library_Open = 1
    if (__main__.G.Library_Open == 2):
        if (__main__.G.Guard1_Killed == 0 and __main__.G.Guard2_Killed == 0):
            __main__.FindPlayer().AwardExperience("Library02")
            
#Masquerade violation for killing kindred in public, added by Malkav, changed by wesp
def checkFieryDeath(name):
    masq = 0
    dist = 600      # normal vision range for open spaces
    p1 = Find(name).GetCenter()
    alleys = FindList("Trigger_Prostitut*") + FindList("jewbkdr")
    for alley in alleys:
        p2 = alley.GetCenter()
        if(distanceSquared(p1, p2) < 40000): dist = 150     # 40000 -> 200 around trigger, 150 reduced visibility in alleys
    distsq = dist * dist
    guys = FindClass("npc_VCop") + FindClass("npc_VDialogPedestrian") + FindClass("npc_VPedestrian") + FindClass("npc_VHuman") + FindClass("npc_VHumanCombatant")
    for guy in guys:
        p2 = guy.GetCenter()
        if(distanceSquared(p1, p2) < distsq): masq = 1
    if (masq == 1 and __main__.G.Patch_Plus == 1): __main__.FindPlayer().ChangeMasqueradeLevel(1)            

#HAVEN: Used to give silver ring, added by Wesp5
def spawnRing():
    pc = __main__.FindPlayer()
    if (pc.AmmoCount("item_g_ring_silver") == 0):
        pc.GiveItem("item_g_ring_silver")
    else:
        pc.GiveAmmo("item_g_ring_silver",1)

#HOSPITAL: Called to unhide the business card, added by wesp
def milliganCard():
    world = Find("world")
    world.SetSafeArea(2)
    if (not __main__.IsDead("Milligan")):
        card = Find("card")
        if card: card.ScriptUnhide()
        sparklies = Find("card_sparklies")
        if sparklies: sparklies.ScriptUnhide()

#HOSPITAL: Called when Pisha leaves, added by wesp
def pishaGone():
    if (__main__.G.Story_State >= 85 and __main__.G.Pisha_Know == 1):
        pisha = Find("Pisha")
        if pisha: pisha.Kill()
        book = Find("book")
        if book: book.Kill()
        corpse = Find("corpse1")
        if corpse: corpse.Kill()

#JEWELRY: Isaac gift, added by wesp
def IsaacGift():
    if (__main__.G.Isaac_Gift == 1):
        __main__.G.Isaac_Gift = 2

#KAMIKAZE ZEN: Turns timer off and light on, added by wesp
def checkTimer():
    timer = Find("virus_timer")
    power = Find("poweron")
    if (__main__.G.Shubs_Act == 4):
        power.Trigger()
        if timer: timer.Kill()

#LIBRARY: Removing vacuum tube box and library card, added by wesp
def useBox():
    pc = __main__.FindPlayer()
    if (pc.HasItem("item_w_claws_protean5")):
        pc.RemoveItem("item_w_claws_protean5")
        pc.SetQuest("Library", 5)
def useCard():
    pc = __main__.FindPlayer()
    if (pc.HasItem("item_w_claws_protean4")):
        pc.RemoveItem("item_w_claws_protean4")
        __main__.G.Card_Inserted = 1

#LIBRARY: Unhiding and hiding the library level switch, added by wesp
def unhideKey():
    pc = __main__.FindPlayer()
    switch = Find("cult_switch")
    switch.ScriptUnhide()
    switch_off = Find("cult_switch_off")
    switch_off.ScriptHide()
    __main__.G.Switch_Unlocked = 1
    if (__main__.G.Switch_Found == 0):
        pc.SetQuest("Library", 6)
        __main__.G.Switch_Found = 1
def hideKey():
    switch = Find("cult_switch")
    switch.ScriptHide()
    switch_off = Find("cult_switch_off")
    switch_off.ScriptHide()
    __main__.G.Switch_Unlocked = 0

#LIBRARY: Ritual chamber, added by wesp and EntenSchreck
def foundRitualChamber():
    gender = __main__.FindPlayer().IsMale()
    __main__.G.Andrei_Library = 1
    __main__.FindPlayer().SetQuest("Library", 7)
    if (__main__.IsClan(__main__.FindPlayer(), "Malkavian") and gender):
        change = Find("Victim")
        change.SetModel("models/character/pc/male/nosferatu/armor0/Nosferatu.mdl")
    if __main__.G.Guard1_Killed == 2:
        guard = Find("guard1")
        guard.ScriptHide()
        gun = Find("gun")
        gun.ScriptUnhide()
        gun_node = Find("gun_node")
        gun_node.ScriptUnhide()
        dead_guard = __main__.CreateEntityNoSpawn("prop_ragdoll", (-50, 1300, 576), (0, 70, 0))
        dead_guard.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(dead_guard)
def PersonalStuntman():
    pc=__main__.FindPlayer()
    E = Find("Stuntman")
    E.SetModel(pc.model)
    #E.SetOrigin(pc.GetOrigin())
    E.ScriptUnhide()
    Find("player_approach_Priest").BeginSequence()
    Find("!playerController").SetOrigin(Find("LovelyPlace").GetOrigin())
def TurnAroundBrother():
    Find("Priest").SetAngles(Find("Execution_Priest").GetAngles())
def defeatedAndrei():
    __main__.FindPlayer().SetQuest("Library", 8)
    __main__.G.Jumbles_Removed = 2
    __main__.ccmd.vamplight=""
    __main__.ccmd.vampexpo=""

#MALKAVIAN 2: Fix for candle skins, added by vladdmaster
def librarySwitcherLightToggle( number ):
    switch = __main__.Find("library_light_switch_%d" % number )
    if (__main__.G.MalkavianMansion_Library_Lights[number-1] == 1):
        switch.skin = 1
    else:
        switch.skin = 0

#OBSERVATORY 2: Near werewolf, added by wesp
def fightWerewolf():
    pc = __main__.FindPlayer()
    if (pc.HasWeaponEquipped("item_w_avamp_blade") or pc.HasWeaponEquipped("item_w_bush_hook") or
pc.HasWeaponEquipped("item_w_claws") or pc.HasWeaponEquipped("item_w_fireaxe") or pc.HasWeaponEquipped("item_w_katana") or pc.HasWeaponEquipped("item_w_occultblade") or pc.HasWeaponEquipped("item_w_sledgehammer")):
        __main__.G.Player_Melee = 1
    else:
        __main__.G.Player_Melee = 0
    if (pc.HasWeaponEquipped("item_w_colt_anaconda") or pc.HasWeaponEquipped("item_w_crossbow") or pc.HasWeaponEquipped("item_w_crossbow_flaming") or pc.HasWeaponEquipped("item_w_deserteagle") or pc.HasWeaponEquipped("item_w_flamethrower") or pc.HasWeaponEquipped("item_w_ithaca_m_37") or pc.HasWeaponEquipped("item_w_rem_m_700_bach") or pc.HasWeaponEquipped("item_w_remington_m_700") or pc.HasWeaponEquipped("item_w_steyr_aug") or pc.HasWeaponEquipped("item_w_supershotgun")):
        __main__.G.Player_Ranged = 1
    else:
        __main__.G.Player_Ranged = 0
        
#OBSERVATORY 2: Kill werewolf, added by wesp
def killWerewolf():
    werewolf = Find("werewolf")
    center = werewolf.GetCenter()
    point = (center[0], center[1], center[2])
    dead_werewolf = __main__.CreateEntityNoSpawn("prop_ragdoll", point, (0,0,0) )
    dead_werewolf.SetModel("models/character/monster/werewolf/werewolf.mdl")
    dead_werewolf.SetName("dead_werewolf")
    __main__.CallEntitySpawn(dead_werewolf)
    werewolf.Kill()

#OCEANHOUSE: Swaps Dodge powerup and book, added by wesp
def dodgeState():
    if (__main__.G.Patch_Plus == 1):
        trunk = Find("Occult_Container")
        trunk.SpawnItemInContainer("item_p_research_lg_dodge")
    else:
        trunk = Find("Occult_Container")
        trunk.SpawnItemInContainer("item_p_occult_dodge")

#RAMEN SHOP: If threatening yukie, added by wesp
def onYukieThreat():
    sword = Find("sword")
    if (__main__.G.Yukie_Threat == 1):
        if sword: sword.Kill()

#RED DRAGON: Float in elevator, added by wesp
def floatElevator():
    hos = Find("Hostess")
    if (not __main__.IsDead("Hostess")):
        if (__main__.G.Hos_Float == 0):
            if (__main__.IsClan(__main__.FindPlayer(), "Malkavian")):
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line1_col_n.mp3")
            else:
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line1_col_e.mp3")
        if (__main__.G.Hos_Float == 1):
            if (__main__.IsClan(__main__.FindPlayer(), "Malkavian")):
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line2_col_n.mp3")
            else:
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line2_col_e.mp3")
        if (__main__.G.Hos_Float == 2):
            if (__main__.IsClan(__main__.FindPlayer(), "Malkavian")):
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line3_col_n.mp3")
            else:
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line3_col_e.mp3")
        if (__main__.G.Hos_Float == 3):
            if (__main__.IsClan(__main__.FindPlayer(), "Malkavian")):
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line4_col_n.mp3")
            else:
                hos.PlayDialogFile("Character/dlg/Chinatown/hostess/line4_col_e.mp3")
        __main__.G.Hos_Float = __main__.G.Hos_Float + 1
        if (__main__.G.Hos_Float == 4):
            __main__.G.Hos_Float = 0

#REDSPOT: Called to see if Slater and Spicoli are alive, added by wesp
def slaterAlive():
    slater = Find("Slater")
    spicoli = Find("Spicoli")
    if (__main__.IsDead("Slater")):
        if(slater): slater.Kill()
    if (__main__.IsDead("Spicoli")):
        if(spicoli): spicoli.Kill()

#SANTA MONICA: Spawns blueblood watch, added by Wesp5
def spawnWatch():
    pc = __main__.FindPlayer()
    if (pc.AmmoCount("item_g_watch_fancy") == 0):
        pc.GiveItem("item_g_watch_fancy")
    else:
        pc.GiveAmmo("item_g_watch_fancy",1)

#SEWERS: Changes model of running Nosferatu, added by wesp
def nosCheck():
    nos = Find("scene_nos")
    nos_model = "models/character/pc/female/nosferatu/armor0/Nosferatu_Female_Armor_0.mdl"
    pc = __main__.FindPlayer()
    gender = pc.IsMale()
    if (gender == 1):
        nos.SetModel(nos_model)
    if (__main__.G.Patch_Plus == 1):
        nos.SetName("scenenos")

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button G, added by vladdmaster
def callbuttonground():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("sixtoground")
    ffive = __main__.Find("fivetoground")
    ffour = __main__.Find("fourtoground")
    fthree = __main__.Find("threetoground")
    ftwo = __main__.Find("twotoground")
    fground = __main__.Find("onground")
    if height[2] >= 1584:
        fsix.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffive.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 974:
        ffour.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 670:
        fthree.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 366:
        ftwo.Trigger()
        pointarr.SetSkin( 2 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 2 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 1, added by vladdmaster
def callbuttonone():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("sixtoone")
    ffive = __main__.Find("fivetoone")
    ffour = __main__.Find("fourtoone")
    fthree = __main__.Find("threetoone")
    fone = __main__.Find("onfirst")
    if height[2] >= 1584:
        fsix.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffive.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 974:
        ffour.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 670:
        fthree.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 366:
        fone.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 62:
        fone.Trigger()
    else:
        fone.Trigger()
        pointarr.SetSkin( 1 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 2, added by vladdmaster
def callbuttontwo():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("sixtotwo")
    ffive = __main__.Find("fivetotwo")
    ffour = __main__.Find("fourtotwo")
    ftwo = __main__.Find("onsecond")
    fground = __main__.Find("groundtotwo")
    if height[2] >= 1584:
        fsix.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffive.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 974:
        ffour.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 670:
        ftwo.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 366:
        ftwo.Trigger()
    elif height[2] >= 62:
        ftwo.Trigger()
        pointarr.SetSkin( 1 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 1 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 3, added by vladdmaster
def callbuttonthree():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("sixtothree")
    ffive = __main__.Find("fivetothree")
    fthree = __main__.Find("onthird")
    fone = __main__.Find("onetothree")
    fground = __main__.Find("groundtothree")
    if height[2] >= 1584:
        fsix.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffive.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 974:
        fthree.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 670:
        fthree.Trigger()
    elif height[2] >= 366:
        fthree.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 62:
        fone.Trigger()
        pointarr.SetSkin( 1 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 1 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 4, added by vladdmaster
def callbuttonfour():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("sixtofour")
    ffour = __main__.Find("onfourth")
    ftwo = __main__.Find("twotofour")
    fone = __main__.Find("onetofour")
    fground = __main__.Find("groundtofour")
    if height[2] >= 1584:
        fsix.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffour.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 974:
        ffour.Trigger()
    elif height[2] >= 670:
        ffour.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 366:
        ftwo.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 62:
        fone.Trigger()
        pointarr.SetSkin( 1 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 1 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 5, added by vladdmaster
def callbuttonfive():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    ffive = __main__.Find("onfifth")
    fthree = __main__.Find("threetofive")
    ftwo = __main__.Find("twotofive")
    fone = __main__.Find("onetofive")
    fground = __main__.Find("groundtofive")
    if height[2] >= 1584:
        ffive.Trigger()
        pointarr.SetSkin( 2 )
    elif height[2] >= 1278:
        ffive.Trigger()
    elif height[2] >= 974:
        ffive.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 670:
        fthree.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 366:
        ftwo.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 62:
        fone.Trigger()
        pointarr.SetSkin( 1 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 1 )

#SKYLINE: Called to add glow to elevator pointing arrows and mark floors, button 6, added by vladdmaster
def callbuttonsix():
    elev = __main__.Find("skyelev")
    height = elev.GetOrigin()
    pointarr = __main__.Find("elevarr")
    fsix = __main__.Find("onsixth")
    ffour = __main__.Find("fourtosix")
    fthree = __main__.Find("threetosix")
    ftwo = __main__.Find("twotosix")
    fone = __main__.Find("onetosix")
    fground = __main__.Find("groundtosix")
    if height[2] >= 1584:
        fsix.Trigger()
    elif height[2] >= 1278:
        fsix.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 974:
        ffour.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 670:
        fthree.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 366:
        ftwo.Trigger()
        pointarr.SetSkin( 1 )
    elif height[2] >= 62:
        fone.Trigger()
        pointarr.SetSkin( 1 )
    else:
        fground.Trigger()
        pointarr.SetSkin( 1 )

#SOCIETY 3: Ash's cell key, added by wesp
def keyState():
    if (__main__.G.Ash_Leave == 1 and __main__.G.Patch_Plus == 1):
        key = Find("ashkey")
        keynode = Find("ashkeynode")
        if key: key.ScriptUnhide()
        if keynode: keynode.ScriptUnhide()

#SOCIETY 3: Saving Ash, added by wesp
def ashDies():
    if (__main__.G.Patch_Plus == 1):
        pc = __main__.FindPlayer()
        state = pc.GetQuestState("Ash")
        if (state == 1):
            pc.SetQuest("Ash", 3)
        if (pc.humanity >= 4):
            ChangeHumanity( -1,3 )

#SOCIETY 4: Bach dropping weapons, added by wesp
def bachDeath():
    if (__main__.G.Patch_Plus == 1):
        bach = Find("Bach")
        center = bach.GetCenter()
        point = (center[0], center[1], center[2] + 20)
        blade = __main__.CreateEntityNoSpawn("item_w_katana", point, (0,0,0) )
        blade.SetName("katana")
        sparklies = __main__.CreateEntityNoSpawn("inspection_node", point, (0,0,0) )
        sparklies.SetParent("katana")
        __main__.CallEntitySpawn(blade)
        __main__.CallEntitySpawn(sparklies)
        swat = __main__.CreateEntityNoSpawn("item_w_rem_m_700_bach", point, (0,0,0) )
        swat.SetName("rifle")
        sparklies1 = __main__.CreateEntityNoSpawn("inspection_node", point, (0,0,0) )
        sparklies1.SetParent("rifle")
        __main__.CallEntitySpawn(swat)
        __main__.CallEntitySpawn(sparklies1)

#TEMPLE 1: Yukie, added by wesp
def YukieFloat(n):
    yukie = Find("Yukie")
    if (yukie and __main__.G.Patch_Plus == 1):
        yukie.PlayDialogFile("Character/dlg/Chinatown/yukie/line%d_col_e.mp3" %n)

#TUTORIAL: SM haven key, added by wesp
def GetKey():
    pc = __main__.FindPlayer()

#TUTORIAL: Dialogue popups, added by wesp
def testGuard():
    if __main__.G.Tut_Secg == 1:
        pc = __main__.FindPlayer()
        if IsClan(pc,"Ventrue") or IsClan(pc, "Tremere"):
            Find("popup_65").OpenWindow()
        elif IsClan(pc, "Malkavian"):
            Find("popup_66").OpenWindow()
        elif IsClan(pc, "Nosferatu"):
            Find("popup_67").OpenWindow()
        elif IsClan(pc, "Brujah") or IsClan(pc, "Toreador"):
            Find("popup_68").OpenWindow()
        else:
            Find("popup_59").OpenWindow()
    else:
        guard = Find("Tutorial_Security_Guard")
        guard.WillTalk(0)
        if __main__.G.Tut_Secg == 2:
            script = Find("sTalkguy_move")
            if script: script.BeginSequence()

#VENTRUETOWER 1: Collateral damage after Sabbat attack, added by Malkav
def collateral():
    G = __main__.G
    if(G.Story_State >= 70 and G.Clean_Rubble == 0 and G.Guard_Drop == 0):
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (33.1819, 829.631, -7358.53), (28, 220, 0))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (115.954, 801.695, -7358.01), (-47.9903, 178.89, 91.4943))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-22.5817, 783.453, -7356.66), (-25.386, 310.587, -20.1677))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-43.8232, 234.327, -7343.78), (-36.9034, 21.6965, 0.91747))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-174.511, 320.242, -7327.69), (0, 291, 0))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-312.208, 407.893, -7351.82), (10, 300, 0))
        cop.SetModel("models/character/npc/common/super_swat/super_swat.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-360.484, 466.291, -7351.82), (0, 309, 60))
        cop.SetModel("models/character/npc/common/super_swat/super_swat.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-625.617, 612.877, -7520.29), (-62.9957, 179.019, -88.8988))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        cop = __main__.CreateEntityNoSpawn("prop_ragdoll", (-521.79, 835.889, -7397.78), (-62.9957, 266.519, -88.8988))
        cop.SetModel("models/character/npc/common/security_guard/security_guard_skinny/security_guard_skinny.mdl")
        __main__.CallEntitySpawn(cop)
        G.Guard_Drop = 1
    elif(G.Story_State >= 70 and G.Clean_Rubble == 1):
        bodies = FindClass("prop_ragdoll")
        for body in bodies: body.Kill()

#VENTRUETOWER 2: Setup timer for plus patch, added by wesp
def setupTimer():
    if (__main__.G.Patch_Plus == 1):
        timer = Find("explosion_timer")
        timer.count_time = 30
        timer.RestartTimer()
        timer.StartTimer()
        timer.Show()

#VENTRUETOWER 2: Check if player has the astrolite, added by wesp
def checkBomb():
    pc = __main__.FindPlayer()
    explosion_timer = __main__.Find("explosion_timer")
    if pc.HasItem("item_g_astrolite") and __main__.G.Story_State >= 100 and __main__.G.Bomb_Disarmed == 0:
        if explosion_timer: explosion_timer.Kill()
        sound = __main__.Find("disarm_bomb")
        if sound: sound.PlaySound()
        __main__.G.Bomb_Disarmed = 1

#VENTRUETOWER 2: Gender of Ventrue enemies, added by wesp
def genderVentrue():
    pc = __main__.FindPlayer()
    gender = pc.IsMale()
    clan = pc.clan
    sniper1 = Find("sniper_1")
    sniper2 = Find("sniper_2")
    patrol4 = Find("patroller_4")
    office1 = Find("office_guard_1")
    office2 = Find("office_guard_2")
    ventrue_female = "models/character/pc/female/ventrue/armor3/ventrue_female_armor_3.mdl"
    if(gender == 1 and clan == 8):
        sniper1.SetModel(ventrue_female)
        sniper2.SetModel(ventrue_female)
        patrol4.SetModel(ventrue_female)
        office1.SetModel(ventrue_female)
        office2.SetModel(ventrue_female)
    if __main__.G.Patch_Plus == 1:
        patrol4.SetScriptedDiscipline("presence 3")
        office1.SetScriptedDiscipline("fortitude 3")
        office2.SetScriptedDiscipline("fortitude 3")

#VENTRUETOWER 3: Sheriff uses Bat's Communion, added by EntenSchreck
def SheriffBatsIn():
    if not Find("Bats") and __main__.G.BatsIn == 0:
        pc=__main__.FindPlayer()
        Bats=__main__.CreateEntityNoSpawn("npc_VHuman",pc.GetOrigin(),pc.GetAngles())
        Bats.SetName("Bats")
        __main__.CallEntitySpawn(Bats)
        Bats = Find("Bats")
        if Bats:
	    Bats.MakeInvincible(1)
            Bats.SetParent("!player")
            Bats.SetModel("models/weapons/disciplines/animalism/world/bats_group_01.mdl")
            Find("bats_in").BeginSequence()
def SheriffBatsOut():
    if Find("Bats"):
        pc=__main__.FindPlayer()
        Bats2=__main__.CreateEntityNoSpawn("npc_VHuman",pc.GetOrigin(),pc.GetAngles())
        Bats2.SetName("Bats2")
        __main__.CallEntitySpawn(Bats2)
        Bats = Find("Bats2")
        if Bats2:
	    Bats2.MakeInvincible(1)
            Bats2.SetParent("!player")
            Bats2.SetModel("models/weapons/disciplines/animalism/world/bats_group_01.mdl")
            Find("bats_out").BeginSequence()
	    __main__.G.Sheriff_Hits=0
	    #Find("Bats").Kill()
	    __main__.ScheduleTask(0.2,'Find("Bats").Kill()')
	    __main__.G.BatsIn = 0
def EffectOnPlayer():
    pc=__main__.FindPlayer()
    i = randint(2, 4)
    pc.Bloodloss(i)	#damages player as well!
    SheriffBatsOut()
    print "No creepy bats that spawned out of nowhere were hurt in this fight..."
def HitCounter():
    G = __main__.G
    if G.Patch_Plus == 1:
    	G.Sheriff_Hits = G.Sheriff_Hits + 1
    	print(__main__.G.Sheriff_Hits)
    	i = randint(3, 5)
    	if G.Sheriff_Hits > i:
    	#if G.Sheriff_Hits == 1:	#TEST
	    SheriffBatsIn()
	    G.BatsIn = 1	#prevents bats from spawning too often if player uses machine gun
def SheriffBatsSummon():
    Find("Swarm_1").ScriptUnhide()
    Find("Swarm_2").ScriptUnhide()
    Find("Swarm_3").ScriptUnhide()
    Find("Swarm_4").ScriptUnhide()
    Find("Swarm_5").ScriptUnhide()
    Find("Swarm_6").ScriptUnhide()
    Find("Swarm_7").ScriptUnhide()
    Find("Swarm_8").ScriptUnhide()
    Find("Swarm_9").ScriptUnhide()
    Find("Swarm_10").ScriptUnhide()
    Find("Swarm_11").ScriptUnhide()
    Find("Swarm_12").ScriptUnhide()
    Find("Swarm_13").ScriptUnhide()
    Find("Swarm_14").ScriptUnhide()

#WARRENS: Updates Bertram quest, added by wesp
def checkCD():
    if (__main__.G.Patch_Plus == 1 and __main__.G.Bertram_RAM == 1):
        pc = __main__.FindPlayer()
        pc.SetQuest("BertramCD", 2)

#Animations for firstperson Thaumaturgy hand, added by Entenschreck, improved by wesp
def checkDiscipline():
    c  = __main__.ccmd
    pc = __main__.FindPlayer()
    if (pc.HasItem("item_w_tzimisce2_head")):
        print 'YOU SHALL NOT CAST!'
    else:
        if (pc.active_blood_healing > 0): c.vm_bloodheal=""
        c.vdiscipline_last=""
        VM()
def VM():
    c  = __main__.ccmd
    G  = __main__.G
    pc = __main__.FindPlayer()
    c.vm_clearlist=""
    if pc.HasItem("item_i_written"):
        c.vm_charge="" #first one is always skipped
        c.vm_charge=""
    else:
        c.vm_draw="" #first one is always skipped
        c.vm_draw=""
    #Need a delay here!
    __main__.ScheduleTask(0.05,"VMHelper()")
def VMHelper():
    c  = __main__.ccmd
    G  = __main__.G
    pc = __main__.FindPlayer()
    if pc.HasItem("item_i_written"):
        c.vm_continue=""
        c.vm_hold=""
        c.vm_reset=""
    else:
        c.vm_idle=""
    c.vm_lower=""
    #View list
    #c.vdebug_wpn_anims_cycle_list=""

#Clan specific idle animations, added by EntenSchreck, improved by malkav and wesp
def IsIdling():
    #__main__.checkOccult()
    __main__.checkBomb()
    pc = __main__.FindPlayer()
    G  = __main__.G
    G.Pos_One = pc.GetOrigin()
    __main__.ScheduleTask(3.0,"AThingOfSomeKind()")
    #__main__.ScheduleTask(1.0,"game_mechanics.AnotherThingOfSomeKind()")
    timer = __main__.FindEntityByName("idle_timer")
    if timer: timer.Disable()
    #Animal Friendship
    #if G.FeatValue == G.FeatValueHelper: pass
    #else: game_mechanics.GetFeatValue() 
def AThingOfSomeKind():
    pc = __main__.FindPlayer()
    G  = __main__.G
    ST = __main__.ScheduleTask
    c  = __main__.ccmd
    notIdle = 0
    gender = 0
    clan = 1  #Human
    postwo = pc.GetOrigin()
    if(postwo[0] != G.Pos_One[0] or postwo[1] != G.Pos_One[1]):
        notIdle = 1
        print "no anims, moving"
    elif(G.InCombat == 1):
        notIdle = 1
        print "no anims, in combat"
    elif(G.No_Idle == 1):
        notIdle = 1
        print "no anims, outside conditions"
    elif((pc.GetCenter()[2] - pc.GetOrigin()[2]) <= 18):
        notIdle = 1
        print "no anims, crouched or prone"
    elif(G.Anims_Disabled == 0):
        npcs = FindClass("npc_V*")
        for npc in npcs:
            p2 = npc.GetOrigin()
            dist = distanceSquared(postwo, p2)
            if(dist < 3200):	#distance: 80 - npcs can't be closer than 41.0044. Player is most likely feeding if any npc is closer. Changed to 80 because of forced dialogues.
                notIdle = 1
                G.Delay = 1 #how many times animations are skipped after feeding
                print "no anims, pc near npc"
                break
    if(notIdle == 0 and pc.active_protean < 2 and pc.HasWeaponEquipped("item_w_unarmed")):
        #This version supports custom models
        BruM1="models/character/pc/male/brujah/armor0/brujah_male_armor_0.mdl"
        BruM2="models/character/pc/male/brujah/armor1/brujah_male_armor_1.mdl"
        BruM3="models/character/pc/male/brujah/armor2/brujah_male_armor_2.mdl"
        BruM4="models/character/pc/male/brujah/armor3/brujah_male_armor_3.mdl"
        BruF1="models/character/pc/female/brujah/armor0/brujah_female_armor_0.mdl"
        BruF2="models/character/pc/female/brujah/armor1/brujah_female_armor_1.mdl"
        BruF3="models/character/pc/female/brujah/armor2/brujah_female_armor_2.mdl"
        BruF4="models/character/pc/female/brujah/armor3/brujah_female_armor_3.mdl"
        GanM1="models/character/pc/male/gangrel/armor_0/Gangrel_Male_Armor_0.mdl"
        GanM2="models/character/pc/male/gangrel/armor_1/Gangrel_Male_Armor_1.mdl"
        GanM3="models/character/pc/male/gangrel/armor_2/Gangrel_Male_Armor_2.mdl"
        GanM4="models/character/pc/male/gangrel/armor_3/Gangrel_Male_Armor_3.mdl"
        GanF1="models/character/pc/female/gangrel/armor0/Gangrel_female_Armor_0.mdl"
        GanF2="models/character/pc/female/gangrel/armor1/Gangrel_female_Armor_1.mdl"
        GanF3="models/character/pc/female/gangrel/armor2/Gangrel_female_Armor_2.mdl"
        GanF4="models/character/pc/female/gangrel/armor3/Gangrel_female_Armor_3.mdl"
        MalM1="models/character/pc/male/malkavian/armor0/Malkavian_Male_Armor_0.mdl"
        MalM2="models/character/pc/male/malkavian/armor1/Malkavian_Male_Armor_1.mdl"
        MalM3="models/character/pc/male/malkavian/armor2/Malkavian_Male_Armor_2.mdl"
        MalM4="models/character/pc/male/malkavian/armor3/Malkavian_Male_Armor_3.mdl"
        MalF1="models/character/pc/female/malkavian/armor0/Malkavian_Female_Armor_0.mdl"
        MalF2="models/character/pc/female/malkavian/armor1/Malk_girl_Armor_1.mdl"
        MalF3="models/character/pc/female/malkavian/armor2/Malk_girl_Armor_2.mdl"
        MalF4="models/character/pc/female/malkavian/armor3/Malk_girl_Armor_3.mdl"
        NosM1="models/character/pc/male/nosferatu/armor0/Nosferatu.mdl"
        NosM2="models/character/pc/male/nosferatu/armor1/Nosferatu_Male_armor_1.mdl"
        NosM3="models/character/pc/male/nosferatu/armor2/Nosferatu_Male_armor_2.mdl"
        NosM4="models/character/pc/male/nosferatu/armor3/Nosferatu_Male_armor_3.mdl"
        NosF1="models/character/pc/female/nosferatu/armor0/nosferatu_Female_Armor_0.mdl"
        NosF2="models/character/pc/female/nosferatu/armor1/nosferatu_Female_Armor_1.mdl"
        NosF3="models/character/pc/female/nosferatu/armor2/nosferatu_Female_Armor_2.mdl"
        NosF4="models/character/pc/female/nosferatu/armor3/nosferatu_Female_Armor_3.mdl"
        TorM1="models/character/pc/male/toreador/armor0/toreador_Male_Armor_0.mdl"
        TorM2="models/character/pc/male/toreador/armor1/toreador_Male_Armor_1.mdl"
        TorM3="models/character/pc/male/toreador/armor2/toreador_Male_Armor_2.mdl"
        TorM4="models/character/pc/male/toreador/armor3/toreador_Male_Armor_3.mdl"
        TorF1="models/character/pc/female/toreador/armor0/toreador_Female_Armor_0.mdl"
        TorF2="models/character/pc/female/toreador/armor1/toreador_Female_Armor_1.mdl"
        TorF3="models/character/pc/female/toreador/armor2/toreador_Female_Armor_2.mdl"
        TorF4="models/character/pc/female/toreador/armor3/toreador_Female_Armor_3.mdl"
        TreM1="models/character/pc/male/tremere/armor0/tremere_Male_Armor_0.mdl"
        TreM2="models/character/pc/male/tremere/armor1/tremere_Male_Armor_1.mdl"
        TreM3="models/character/pc/male/tremere/armor2/tremere_Male_Armor_2.mdl"
        TreM4="models/character/pc/male/tremere/armor3/tremere_Male_Armor_3.mdl"
        TreF1="models/character/pc/female/tremere/armor0/tremere_Female_Armor_0.mdl"
        TreF2="models/character/pc/female/tremere/armor1/tremere_Female_Armor_1.mdl"
        TreF3="models/character/pc/female/tremere/armor2/tremere_Female_Armor_2.mdl"
        TreF4="models/character/pc/female/tremere/armor3/tremere_Female_Armor_3.mdl"
        VenM1="models/character/pc/male/ventrue/armor0/ventrue_Male_Armor_0.mdl"
        VenM2="models/character/pc/male/ventrue/armor1/ventrue_Male_Armor_1.mdl"
        VenM3="models/character/pc/male/ventrue/armor2/ventrue_Male_Armor_2.mdl"
        VenM4="models/character/pc/male/ventrue/armor3/ventrue_Male_Armor_3.mdl"
        VenF1="models/character/pc/female/ventrue/armor0/ventrue_Female_Armor_0.mdl"
        VenF2="models/character/pc/female/ventrue/armor1/ventrue_Female_Armor_1.mdl"
        VenF3="models/character/pc/female/ventrue/armor2/ventrue_Female_Armor_2.mdl"
        VenF4="models/character/pc/female/ventrue/armor3/ventrue_Female_Armor_3.mdl"
        #Beast="models/character/monster/animalism_beastform/animalism_beastform.mdl" #Protean
        if pc.model==BruM1 or pc.model==BruM2 or pc.model==BruM3 or pc.model==BruM4:
            clan=2
            gender=1
        elif pc.model==BruF1 or pc.model==BruF2 or pc.model==BruF3 or pc.model==BruF4:
            clan=2
        elif pc.model==GanM1 or pc.model==GanM2 or pc.model==GanM3 or pc.model==GanM4:
            clan=3
            gender=1
        elif pc.model==GanF1 or pc.model==GanF2 or pc.model==GanF3 or pc.model==GanF4:
            clan=3
        elif pc.model==MalM1 or pc.model==MalM2 or pc.model==MalM3 or pc.model==MalM4:
            clan=4
            gender=1
        elif pc.model==MalF1 or pc.model==MalF2 or pc.model==MalF3 or pc.model==MalF4:
            clan=4
        elif pc.model==NosM1 or pc.model==NosM2 or pc.model==NosM3 or pc.model==NosM4:
            clan=5
            gender=1
        elif pc.model==NosF1 or pc.model==NosF2 or pc.model==NosF3 or pc.model==NosF4:
            clan=5
        elif pc.model==TorM1 or pc.model==TorM2 or pc.model==TorM3 or pc.model==TorM4:
            clan=6
            gender=1
        elif pc.model==TorF1 or pc.model==TorF2 or pc.model==TorF3 or pc.model==TorF4:
            clan=6
        elif pc.model==TreM1 or pc.model==TreM2 or pc.model==TreM3 or pc.model==TreM4:
            clan=7
            gender=1
        elif pc.model==TreF1 or pc.model==TreF2 or pc.model==TreF3 or pc.model==TreF4:
            clan=7
        elif pc.model==VenM1 or pc.model==VenM2 or pc.model==VenM3 or pc.model==VenM4:
            clan=8
            gender=1
        elif pc.model==VenF1 or pc.model==VenF2 or pc.model==VenF3 or pc.model==VenF4:
            clan=8
        #elif pc.model==Beast:
        i = randint(1, 7)
        if(gender == 1):
            #Human
            if(clan == 1 and i == 1): c.ArmsCrossed=""
            elif(clan == 1 and i == 2): c.Pissed=""
            elif(clan == 1 and i == 3): c.Pray=""
            elif(clan == 1 and i == 4): c.Lost=""
            #Brujah
            if(clan == 2 and i == 1): c.BruAnim2=""
            elif(clan == 2 and i == 2): c.BruAnim3=""
            elif(clan == 2 and i == 3): c.Lost=""
            elif(clan == 2 and i >= 3): c.BruAnim1=""
            #Gangrel
            if(clan == 3 and i == 1): c.GanAnim2=""
            elif(clan == 3 and i == 2): c.GanAnim3=""
            elif(clan == 3 and i == 3): c.Lost=""
            elif(clan == 3 and i >= 3): c.GanAnim1=""
            #Malkavian
            if(clan == 4 and i == 1): c.MalAnim2=""
            elif(clan == 4 and i == 2): c.Lost=""
            elif(clan == 4 and i == 3): c.Jittery=""
            elif(clan == 4 and i >= 3): c.MalAnim1=""
            #Nosferatu
            if(clan == 5 and i == 1): c.NosAnim2=""
            elif(clan == 5 and i == 2): c.NosAnim3=""
            elif(clan == 5 and i == 3): c.Lost=""
            elif(clan == 5 and i >= 3): c.NosAnim1=""
            #Toreador
            if(clan == 6 and i == 1): c.TorAnim2=""
            elif(clan == 6 and i == 2): c.TorAnim3=""
            elif(clan == 6 and i == 3): c.TorAnim4=""
            elif(clan == 6 and i == 4): c.Lost=""
            elif(clan == 6 and i >= 4): c.TorAnim1=""
            #Tremere
            if(clan == 7 and i == 1): c.TreAnim2=""
            elif(clan == 7 and i == 2): c.TreAnim3=""
            elif(clan == 7 and i == 3): c.Lost=""
            elif(clan == 7 and i >= 3): c.TreAnim1=""
            #Ventrue
            if(clan == 8 and i == 1): c.VenAnim2=""
            elif(clan == 8 and i == 2): c.VenAnim3=""
            elif(clan == 8 and i == 3): c.Lost=""
            elif(clan == 8 and i >= 3): c.VenAnim1=""
        elif(gender == 0):
            #Human
            if(clan == 1 and i == 1): c.ArmsCrossed=""
            elif(clan == 1 and i == 2): c.Pissed=""
            elif(clan == 1 and i == 3): c.Pray=""
            elif(clan == 1 and i == 4): c.Lost=""
            #Brujah
            if(clan == 2 and i == 1): c.BrufemAnim2=""
            elif(clan == 2 and i == 2): c.BrufemAnim2=""
            elif(clan == 2 and i == 3): c.Lost=""
            elif(clan == 2 and i >= 3): c.BrufemAnim1=""
            #Gangrel
            if(clan == 3 and i == 1): c.GanfemAnim1=""
            elif(clan == 3 and i >= 2): c.Lost=""
# disabled by wesp  elif(clan == 3 and i >= 2): c.GanfemAnim2=""
            #Malkavian
            if(clan == 4 and i == 1): c.MalfemAnim2=""
            elif(clan == 4 and i == 2): c.MalfemAnim3=""
            elif(clan == 4 and i == 3): c.MalfemAnim4=""
            elif(clan == 4 and i == 4): c.Lost=""
            elif(clan == 4 and i >= 4): c.MalfemAnim1=""
            #Nosferatu
            if(clan == 5 and i == 1): c.NosfemAnim2=""
            elif(clan == 5 and i == 2): c.NosfemAnim3=""
            elif(clan == 5 and i == 3): c.Lost=""
            elif(clan == 5 and i >= 3): c.NosfemAnim1=""
            #Toreador
            if(clan == 6 and i == 1): c.TorfemAnim2=""
            elif(clan == 6 and i == 2): c.TorfemAnim3=""
            elif(clan == 6 and i == 3): c.Lost=""
            elif(clan == 6 and i >= 3): c.TorfemAnim1=""
            #Tremere
            if(clan == 7 and i == 1): c.TrefemAnim2=""
            elif(clan == 7 and i == 2): c.TrefemAnim3=""
            elif(clan == 7 and i == 3): c.Lost=""
            elif(clan == 7 and i >= 3): c.TrefemAnim1=""
            #Ventrue
            if(clan == 8 and i == 1): c.VenfemAnim2=""
            elif(clan == 8 and i == 2): c.VenfemAnim3=""
            elif(clan == 8 and i == 3): c.Lost=""
            elif(clan == 8 and i >= 3): c.VenfemAnim1=""
#Durations - unused, but kept them if needed in future
#Brujah_HitHands2		1.30
#Brujah_Female_ArmOut2		4.00
#Gangrel_Sniff2			4.50
#Gangrel_Female_Nails1		3.20
#Malkavian_Look2		3.85
#Malk_Female_Stretch2		5.50
#Nos_Howl2			2.50
#Nos_Female_Howl2		2.50
#Toreador_Checknails2		3.22
#Toreador_Female_Nails2		4.35
#Tremere_Rubhands2		5.00
#Tremere_Female_Think2		5.80
#Ventrue_CheckNails2		3.25
#Ventrue_Female_Sexy2		4.90
#Brujah_Bringit2		2.90
#Gangrel_Look2			4.50
#Gangrel_Female_Stretch2	5.50
#Malk_Female_Bend2		5.00
#Nos_Crouch2			5.20
#Nos_Female_Crouch2		5.20
#Toreador_Posing2		3.90
#Toreador_Female_Hair2		3.20
#Tremere_Spell2			5.00
#Tremere_Female_Spell2		5.00
#Ventrue_PhoneCall2		9.90
#Ventrue_Female_Nails2		4.15
#Brujah_Idle2			1.90
#Gangrel_Idle2			2.40
#Malkavian_Idle2		1.90
#Nos_Idle2			2.20
#Toreador_Idle2			2.00
#Tremere_Idle2			2.00
#Ventrue_Idle2			2.00
#Brujah_Female_Idle2		4.00
#Gangrel_Female_Idle2		2.00
#Malk_Female_Idle2		3.00
#Nos_Female_Idle2		2.20
#toreador_Female_Idle2		2.00
#Tremere_Female_Idle2		2.00
#Ventrue_Female_Idle2		2.00
#Malk_Female_Sultry2		11.00
#Toreador_FixHair2		3.07
    elif(notIdle == 0 and pc.active_protean > 1 and pc.HasWeaponEquipped("item_w_unarmed")):
        i = randint(1, 6)
        if(i == 1): c.Howl=""
#        elif(i == 2):
#            c.Alert_Front_into=""
#            ST(3.00,'__main__.ccmd.Alert_Front_outof=""')
#        elif(i == 3):
#            c.Alert_90l_into=""
#            ST(3.00,'__main__.ccmd.Alert_90l_outof=""')
#        elif(i == 4):
#            c.Alert_90r_into=""
#            ST(3.00,'__main__.ccmd.Alert_90r_outof=""')
#        elif(i == 5):
#            c.Alert_180_into=""
#            ST(3.00,'__main__.ccmd.Alert_180_outof=""')
        elif(i == 6): c.Alert_Lookaround=""
    elif G.Delay != 0:
        G.Delay = G.Delay - 1
    timer = __main__.FindEntityByName("idle_timer")
    if timer: timer.Enable()
#Adds random whispers to malkavian lookaround animation, "Ambiguous" or "Danger", added by Entenschreck
def RandomWhisper():
    pc=__main__.FindPlayer()
    print "Selecting Whisper"
    NonHostile = 0
    #Disallow Danger whispers in these areas:
    if Find("Caine"): NonHostile=1
    elif Find("Cabbie"): NonHostile=1
    elif Find("haven_pc"): NonHostile=1
    elif Find("ox"): NonHostile=1
    elif Find("WongHo"): NonHostile=1
    elif Find("Isaac"): NonHostile=1
    elif Find("Damsel"): NonHostile=1
    elif Find("Slater"): NonHostile=1
    elif Find("VV"): NonHostile=1
    elif Find("plus_DJ"): NonHostile=1
    elif Find("Carson_Computer"): NonHostile=1
    elif Find("Vandal"): NonHostile=1
    elif Find("Victor"): NonHostile=1   
    if NonHostile == 1 and __main__.G.InCombat == 0:
        print "Nonhostile area"
        i=randint(0,5)
        if i == 0: pc.Whisper("Crying")
        elif i == 1: pc.Whisper("Gibberish")
        elif i == 2: pc.Whisper("Moaning")
        else: pc.Whisper("Ambiguous")
    else:
        print "Hostile area"
        i=randint(0,5)
        if i == 0: pc.Whisper("Crying")
        elif i == 1: pc.Whisper("Gibberish")
        elif i == 2: pc.Whisper("Moaning")
        else: pc.Whisper("Danger")

#Called by "events_player_plus", added by EntenSchreck
def OnActivateThaumLvl2():
    print "Thaumaturgy Level 2 activated"
def OnActivateThaumLvl1():
    print "Thaumaturgy Level 1 activated"
def OnActivateDominateLvl2():
    print "Dominate Level 2 activated"
def OnActivateDominateLvl1():
    print "Dominate Level 1 activated"
def OnActivateDementationLvl2():
    print "Dementation Level 2 activated"
def OnActivateDementationLvl1():
    print "Dementation Level 1 activated"
def OnActivateAnimalismLvl2():
    print "Animalism Level 2 activated"
def OnActivateAnimalismLvl1():
    print "Animalism Level 1 activated"
def OnActivatePresence():
    print "Presence Level %s activated" % __main__.FindPlayer().base_presence
def OnWolfMorphBegin():
    print "Wolf Morph Begin"
def OnWolfMorphEnd():
    print "Wolf Morph End"
def OnActivateCelerity():
    print "Celerity Level %s activated" % __main__.FindPlayer().base_celerity
def OnActivatePotence():
    print "Potence Level %s activated" % __main__.FindPlayer().base_potence
def OnActivateObfuscate():
    print "Obfuscate Level %s activated" % __main__.FindPlayer().base_obfuscate
def OnActivateFortitude():
    print "Fortitude Level %s activated" % __main__.FindPlayer().base_fortitude
def OnActivateAuspex():
    print "Auspex Level %s activated" % __main__.FindPlayer().base_auspex
def OnActivateProtean():
    print "Protean Level %s activated" % __main__.FindPlayer().base_protean
    if __main__.FindPlayer().base_protean == 5:
        c  = __main__.ccmd
        c.setClaws=""
        __main__.ScheduleTask(2.2,"__main__.ccmd.useClaws=\"\"")
def OnFrenzyBegin():
    print "Frenzy Begin"
    pc=__main__.FindPlayer()
    if pc.HasItem("item_w_tzimisce2_head"):
        pc.RemoveItem("item_w_tzimisce2_head")
    if pc.HasItem("item_i_written"):
        pc.RemoveItem("item_i_written")
def OnFrenzyEnd():
    print "Frenzy End"
def OnPlayerKilled():
    print "Player Dead"
def OnPlayerTookDamage():
    print "Took Damage"

#Called by events_world, added by EntenSchreck
def OnCopsOutside():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnCopsComing():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnStartCopPursuitMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnStartCopAlertMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnEndCopPursuitMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnEndCopAlertMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnStartHunterPursuitMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnEndHunterPursuitMode():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevel1():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevel2():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevel3():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevel4():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevel5():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnMasqueradeLevelChanged():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnPlayerHasNoBlood():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnCombatMusicStart():
    OnBeginCombatMusic()
    if (__main__.G.Patch_Plus == 1):
        pass
def OnCombatMusicEnd():
    OnBeginNormalMusic()
    OnEndCombat()
    if (__main__.G.Patch_Plus == 1):
        pass
def OnAlertMusicStart():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnAlertMusicEnd():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnNormalMusicStart():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnNormalMusicEnd():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnUseBegin():
    if (__main__.G.Patch_Plus == 1):
        pass
def OnUseEnd():
    if (__main__.G.Patch_Plus == 1):
        pass

#Athletics Feat, added by EntenSchreck, unused at the moment
def CalcFeat_Athletics():
    pc   = __main__.FindPlayer()
    cvar = __main__.cvar
    #default values:
    #sv_rollangle 2
    #sv_runscale 1.00
    #sv_sneakscale 2.1
    if pc.CalcFeat("Jumping") == 1:
        cvar.sv_runscale="0.80"
        cvar.sv_rollangle="1"
        cvar.sv_sneakscale="1.55"
    elif pc.CalcFeat("Jumping") == 2:
        cvar.sv_runscale="0.90"
        cvar.sv_rollangle="2"
        cvar.sv_sneakscale="1.7"
    elif pc.CalcFeat("Jumping") == 3:
        cvar.sv_runscale="1.00"
        cvar.sv_rollangle="3"
        cvar.sv_sneakscale="1.85"
    elif pc.CalcFeat("Jumping") == 4:
        cvar.sv_runscale="1.10"
        cvar.sv_rollangle="4"
        cvar.sv_sneakscale="2.0"
    elif pc.CalcFeat("Jumping") == 5:
        cvar.sv_runscale="1.15"
        cvar.sv_rollangle="5"
        cvar.sv_sneakscale="2.2"
    elif pc.CalcFeat("Jumping") == 6:
        cvar.sv_runscale="1.20"
        cvar.sv_rollangle="6"
        cvar.sv_sneakscale="2.4"
    elif pc.CalcFeat("Jumping") == 7:
        cvar.sv_runscale="1.25"
        cvar.sv_rollangle="7"
        cvar.sv_sneakscale="2.6"
    elif pc.CalcFeat("Jumping") == 8:
        cvar.sv_runscale="1.30"
        cvar.sv_rollangle="8"
        cvar.sv_sneakscale="2.8"
    elif pc.CalcFeat("Jumping") == 9:
        cvar.sv_runscale="1.35"
        cvar.sv_rollangle="9"
        cvar.sv_sneakscale="3.0"
    elif pc.CalcFeat("Jumping") == 10:
        cvar.sv_runscale="1.40"
        cvar.sv_rollangle="10"
        cvar.sv_sneakscale="3.2"
    #Just in case...
    elif pc.CalcFeat("Jumping") == 11:
        cvar.sv_runscale="1.45"
        cvar.sv_rollangle="10"
        cvar.sv_sneakscale="3.4"
    elif pc.CalcFeat("Jumping") == 12:
        cvar.sv_runscale="1.50"
        cvar.sv_rollangle="10"
        cvar.sv_sneakscale="3.5"

#Animal Friendship Feat, added by EntenSchreck, unused at the moment
#zur Aktivierung: Animal_Friendship.AnimalRadar()
from __main__ import Character
def _Near(self,loc,r=200):
    # Avoid square root function. very inefficient
    # if (Distance)^2 > (x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2
    loc2=self.GetOrigin()
    xd=loc2[0]-loc[0]
    yd=loc2[1]-loc[1]
    zd=loc2[2]-loc[2]
    return (r*r) > (xd*xd) + (yd*yd) + (zd*zd)
Character.Near=_Near
#makes animals deaf and blind...
def BefriendAnimal(animal):
    animal.SetRelationship("player D_LI 5")
    animal.TweakParam("hearing 0.00")
    animal.TweakParam("vision 0.00")
    animal.pl_investigate=0
    animal.pl_criminal_flee=0
    animal.pl_criminal_attack=0
    animal.pl_supernatural_flee=0
    animal.pl_supernatural_attack=0
    animal.SetInvestigateMode(0)
    animal.SetInvestigateModeCombat(0)
    print "Befriending Animal"
    #print(animal)
#Dogs' Reaction
def OnDogFoundPlayer(Dog):
    print("OnDogFoundPlayer() called by:")
    print(Dog)
    Dog.SetRelationship("player D_NU 0")
    Dog.ChangeSchedule("SCHED_VDOG_SNARL")
def AnimalRadar():
    pc=__main__.FindPlayer()
    PlayerPos = pc.GetOrigin()
    rats=FindClass("Npc_VRat")
    for r in rats:
        if r.Near(pc.GetOrigin(),r.detection_distance) == 1:
            AnimalFriendship(r,1,r.friendship_level)
    cats=FindClass("Npc_VAnimal") #TEMPORARY
    for c in cats:
        if c.Near(pc.GetOrigin(),c.warn_range) == 1:
            AnimalFriendship(r,1,c.friendship_level)
    dogs=FindClass("Npc_VDog")
    for d in dogs:
        if d.Near(pc.GetOrigin(),d.warn_range) == 1:
            #d.ChangeSchedule("SCHED_VDOG_SNARL")
            AnimalFriendship(r,1,d.friendship_level)
def AnimalFriendship(Name,Animal,FriendshipLevel=0):
    pc = __main__.FindPlayer()
    G  = __main__.G
    #Level=pc.CalcFeat("Animal_Friendship")
    #Level=pc.base_charisma+pc.base_seduction
    Level = 10 #TEST
    #Rat
    if Animal == 1:
        if Level >= FriendshipLevel or Level == FriendshipLevel:
            BefriendAnimal(Name)
    #Cat
    if Animal == 2:
        if Level >= FriendshipLevel or Level == FriendshipLevel:
            BefriendAnimal(Name)
            # call scripted_sequence "sit" here!
        else:
            pass
            # call scripted_sequence "cower" here!
    #Dog
    if Animal == 3:
        AnimalName = "%s" % Name
        print(AnimalName)
        if Level >= FriendshipLevel or Level == FriendshipLevel:
            BefriendAnimal(Name)
            Find(AnimalName).ChangeSchedule("SCHED_VDOG_MADEFRIEND")
            E = Find("plus_befriend_"+AnimalName)
            if E: E.BeginSequence()
            E = Find(AnimalNamee+"_hurt")
            if E: E.Disable()
        else:
            Find(AnimalName).ChangeSchedule("SCHED_VDOG_SNARL")
    #Zombie
    if Animal == 4:
        if Level >= FriendshipLevel or Level == FriendshipLevel:
            BefriendAnimal(Name)

##############################################################################
# General Utility Functions
##############################################################################

def Whisper(soundfile):
    from __main__ import pc
    pc.Whisper(soundfile)

#This is empty because this is the name of the function for blood loss timer
#that was used in the original version of CE. Since I moved things to the
#new version of CE, I still have all the map timers but I am too lazy
#to go in and remove them all
def OnBLEvent():
    if(not isCEInstalled()): return
    
def Schedule():
    if(not isCEInstalled()): return
    onOverfeed()
    __main__.ScheduleTask(0.1,"OnNewBLEvent()")


def OnNewBLEvent():
    if(not isCEInstalled() or not isBloodTimerOn()): return
    pc = __main__.FindPlayer()
    G = __main__.G
    BLOOD_MAX_COUNT = 7+pc.stamina
    G.BloodCounter += 1
    print "BloodCounter increased"  #can be removed, except for testing
    while((G.BloodCounter >= BLOOD_MAX_COUNT) and (pc.bloodpool > 1)):
        pc.Bloodloss(1)
        print "Bloodloss 1 Blood point"  #can be removed, except for testing
        G.BloodCounter = G.BloodCounter - BLOOD_MAX_COUNT
    if(G.BloodCounter >= 2* BLOOD_MAX_COUNT):
        try: __main__.ccmd.frenzyplayer()
        except: pass
        print "hunger induced autofrenzy"
    __main__.ScheduleTask(30.0,"OnNewBLEvent()")
    
    
def onOverfeed():
    if(not isCEInstalled()): return
    pc = __main__.FindPlayer()
    G = __main__.G
    BLOOD_MAX_COUNT = 7+pc.stamina
    while((G.BloodCounter <= BLOOD_MAX_COUNT) and (pc.bloodpool >= 16)):
        pc.Bloodloss(1)
        G.BloodCounter = 0
        print "Bloodloss due to overfeeding"    #can be removed, except for testing
    __main__.ScheduleTask(5.0,"onOverfeed()")
#### Bloodtimer and related stuff end ####        
     

def GiveItem(char, ItemName):
    char.GiveItem(ItemName)

def HasItem(char, ItemName):
    return char.HasItem(ItemName)

def RemoveItem(char, ItemName):
    char.RemoveItem(ItemName)

def FrenzyTrigger(char):
    char.FrenzyTrigger(1)

def IsClan(char, ClanName):
    if (char.clan == 0 and ClanName == "None"):
        return 1
    elif (char.clan == 2 and ClanName == "Brujah"):
        return 1
    elif (char.clan == 3 and ClanName == "Gangrel"):
        return 1
    elif (char.clan == 4 and ClanName == "Malkavian"):
        return 1
    elif (char.clan == 5 and ClanName == "Nosferatu"):
        return 1
    elif (char.clan == 6 and ClanName == "Toreador"):
        return 1
    elif (char.clan == 7 and ClanName == "Tremere"):
        return 1
    elif (char.clan == 8 and ClanName == "Ventrue"):
        return 1
    return 0

def IsMale(char):
    return char.IsMale()
    
#Simple function to test whether or not the character is in stealth, i.e. squatting
#Added by burgermeister
#Original code provided by Dheuster
def IsStealth(char):
    squating = ((char.GetCenter()[2] - char.GetOrigin()[2]) == 18)
    return squating
    
    
#Following two function borrowed from Dheu's Companion Mod: http://sites.google.com/site/vtmbcompmodhome/
#Utility functions for keeping Companion NPCs near player
#added by burgermeister 4/09
def TraceLine(char, dist=50):
    """ Locates point directly infront of or behind character on same plain. Use negative value for distance if desire behind """

    from math import pi as _pi
    from math import cos as _cos, sin as _sin

    pos   = char.GetOrigin()
    angle = char.GetAngles()[1]

    # degToRad : r = d/(360/2pi)
    xoffset = dist * _cos((angle/(360/(2*_pi))))
    yoffset = dist * _sin((angle/(360/(2*_pi))))

    return (pos[0]+xoffset, pos[1]+yoffset, pos[2])
    

def Near(char,loc,r=200):
    """ Param 1 = location (x,y,z) Param 2 = radius [default 200]. Imagine sphere around location with radius. If npc is within sphere, returns true"""  

    # Calculate distance between 2 points in 3D:
    # Distance = SquareRoot((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
    # - avoid square root function. very innefficient
    # if (Distance)^2 > (x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2

    loc2=char.GetOrigin()
    xd=loc2[0]-loc[0]
    yd=loc2[1]-loc[1]
    zd=loc2[2]-loc[2]
    return (r*r) > (xd*xd) + (yd*yd) + (zd*zd)    

def IsDead(charname):
    return __main__.G.morgue.has_key(charname)

def MarkAsDead(charname):
    __main__.G.morgue[charname] = 1

def CheckFrenzy(char, value):
    char.FrenzyCheck(value)
    return None

def NumTimesTalkedTo(num):
    if ( npc.times_talked == num ):
        return 1
    else:
        return 0

def RandomLine( NumList ):
    R = Random( time() )
    Index = R.randint(0, len(NumList)-1)
    return NumList[Index]

#Called on the hubs (and possibly other maps?) to place hunters if the player violates the masquerade
def checkMasquerade():
    level = __main__.FindPlayer().GetMasqueradeLevel()
    print "level %i" % level
    if(level >= 2 and level < 5):
        #changed by dan_upright 07/12/04
        G = __main__.G
        if (G.In_Hollywood != 1 or G.Courier_QuickBuck != 1):
            i = 2
            while(i <= level):
                if(huntersDead[i - 2] == 0):
                    spawner = Find("hunter_maker_%i" % (i - 1))
                    if(spawner):
                        spawner.Spawn()
                i = i + 1
        #changes end

#Spawns in the appropriate cop car given the input
def spawnCopCar(i):
    ent = Find("cop_car_%i" % (i))
    if ent: ent.ScriptUnhide()
    ent = Find("cop_front_%i" % (i))
    if ent: ent.Spawn()
    ent = Find("cop_rear_%i" % (i))
    if ent: ent.Spawn()
    ent = Find("red%i" % (i))
    if ent: ent.TurnOn()
    ent = Find("blue%i" % (i))
    if ent: ent.TurnOn()
    ent = Find("cover_front_%i" % (i))
    if ent: ent.ScriptUnhide()
    ent = Find("cover_rear_%i" % (i))
    if ent: ent.ScriptUnhide()

#Removes cop cars that may have been spawned onto the map previously argument specifies the total number of cop cars on the given hub
def removeCopCar(total):
    i = 1
    while(i <= total):
       ent = Find("cop_car_%i" % (i))
       if ent: ent.ScriptHide()
       ent = Find("red%i" % (i))
       if ent: ent.TurnOff()
       ent = Find("blue%i" % (i))
       if ent: ent.TurnOff()
       ent = Find("cover_front_%i" % (i))
       if ent: ent.ScriptHide()
       ent = Find("cover_rear_%i" % (i))
       if ent: ent.ScriptHide()
       i = i + 1
    cops = FindList("stake_out_cop")
    for cop in cops:
        cop.Kill()
    cops = FindList("cop")
    for cop in cops:
        cop.Kill()
    cops = FindList("patrol_cop_1")
    for cop in cops:
        cop.Kill()
    cops = FindList("patrol_cop_2")
    for cop in cops:
        cop.Kill()

#Returns the distanceSquared between two 3D points
def distanceSquared(p1, p2):
    xDistance = (p1[0] - p2[0]) * (p1[0] - p2[0])
    yDistance = (p1[1] - p2[1]) * (p1[1] - p2[1])
    zDistance = (p1[2] - p2[2]) * (p1[2] - p2[2])
    return (xDistance + yDistance + zDistance)

#Starts the BloodDoll on a random line
def doll1dlg():
    doll = Find("Doll1")
    if(__main__.IsClan(__main__.FindPlayer(), "Nosferatu")):
        return 121
    elif(__main__.G.Doll_Seduce == 1):
        return 91
    else:
        return RandomLine([1, 31, 61])

#HAVEN: Called if heather should change her skin, added by vladdmaster
def heatherSkin():
    G = __main__.G
    IsDead = __main__.IsDead
    heather = Find("Heather")
    if(G.Heather_Outfit == 1):
        heather.SetModel("models/character/npc/unique/Santa_Monica/Heather/Heather_goth.mdl")
    elif(G.Heather_Outfit == 2):
        heather.SetModel("models/character/npc/unique/Santa_Monica/Heather/Heather_3.mdl")
    else:
        heather.SetModel("models/character/npc/unique/Santa_Monica/Heather/Heather.mdl")
    G.Heather_Clothes = 0

#HAVEN: Used to place heather in the various player havens, changed by wesp and vladdmaster
def heatherHavenP():
    G = __main__.G
    IsDead = __main__.IsDead
    heather = Find("Heather")
    if(G.Heather_Haven and not IsDead("Heather") and heather):
        heather.ScriptUnhide()
    if((G.Heather_Gone or (G.Story_State >= 75 and G.Heather_Indoors == 0 and G.Player_Sabbat == 0 and G.Sabbat_Infiltrate == 0)) and heather):
        heather.ScriptHide()
    if(G.Story_State >= 30 and G.Heather_Haven and not IsDead("Heather") and G.Heather_Gone == 0 and G.Story_State < 75 and not G.Heather_Lure):
        G.Mcfly_Present = 1
        mcfly = Find("McFly")
        if mcfly: mcfly.ScriptUnhide()
    if(G.Mcfly_Leave or G.Mcfly_Feed or G.Mcfly_Dominated or G.Mcfly_Dementated or IsDead("McFly")):
        mcfly = Find("McFly")
        if mcfly: mcfly.Kill()
    if(G.Heather_Clothes and heather):
        if not(G.Prince_Skyline or G.Gary_Haven or G.Regent_Family == 3):
            heatherSkin()
#        G.Heather_Outfit = G.Heather_Outfit + 1
#        if(G.Heather_Outfit > 2):
#            G.Heather_Outfit = 0
        G.Heather_Clothes = 0
    if(IsDead("Heather") and heather):
        heather.Kill()
        mcfly = Find("mcfly")
        if mcfly: mcfly.Kill()

#HAVEN: Used to place heather in the various player havens, changed by wesp and vladdmaster
def heatherHavenS():
    G = __main__.G
    IsDead = __main__.IsDead
    heather = Find("Heather")
    if(G.Heather_Haven and not IsDead("Heather") and heather):
        heather.ScriptUnhide()
    if((G.Heather_Gone or (G.Story_State >= 75 and G.Heather_Indoors == 0 and G.Player_Sabbat < 3)) and heather):
        heather.ScriptHide()
    if(G.Story_State >= 30 and G.Heather_Haven and not IsDead("Heather") and G.Heather_Gone == 0 and G.Story_State < 75 and not G.Heather_Lure):
        G.Mcfly_Present = 1
        mcfly = Find("McFly")
        if mcfly: mcfly.ScriptUnhide()
    if(G.Mcfly_Leave or G.Mcfly_Feed or G.Mcfly_Dominated or G.Mcfly_Dementated or IsDead("McFly")):
        mcfly = Find("McFly")
        if mcfly: mcfly.Kill()
    if(G.Heather_Clothes and heather):
        if (G.Prince_Skyline):
            heatherSkin()
#        G.Heather_Outfit = G.Heather_Outfit + 1
#        if(G.Heather_Outfit > 2):
#            G.Heather_Outfit = 0
        G.Heather_Clothes = 0
    if(IsDead("Heather") and heather):
        heather.Kill()
        mcfly = Find("mcfly")
        if mcfly: mcfly.Kill()

#HAVEN: Used to place heather in the various player havens, changed by wesp and vladdmaster
def heatherHavenC():
    G = __main__.G
    IsDead = __main__.IsDead
    heather = Find("Heather")
    if(G.Heather_Haven and not IsDead("Heather") and heather):
        heather.ScriptUnhide()
    if((G.Heather_Gone or (G.Story_State >= 75 and G.Heather_Indoors == 0 and G.Player_Sabbat < 3)) and heather):
        heather.ScriptHide()
    if(G.Story_State >= 30 and G.Heather_Haven and not IsDead("Heather") and G.Heather_Gone == 0 and G.Story_State < 75 and not G.Heather_Lure):
        G.Mcfly_Present = 1
        mcfly = Find("McFly")
        if mcfly: mcfly.ScriptUnhide()
    if(G.Mcfly_Leave or G.Mcfly_Feed or G.Mcfly_Dominated or G.Mcfly_Dementated or IsDead("McFly")):
        mcfly = Find("McFly")
        if mcfly: mcfly.Kill()
    if(G.Heather_Clothes and heather):
        if (G.Regent_Family == 3):
            heatherSkin()
#        G.Heather_Outfit = G.Heather_Outfit + 1
#        if(G.Heather_Outfit > 2):
#            G.Heather_Outfit = 0
        G.Heather_Clothes = 0
    if(IsDead("Heather") and heather):
        heather.Kill()
        mcfly = Find("mcfly")
        if mcfly: mcfly.Kill()

#HAVEN: Used to place heather in the various player havens, changed by wesp and vladdmaster
def heatherHavenN():
    G = __main__.G
    IsDead = __main__.IsDead
    heather = Find("Heather")
    if(G.Heather_Haven and not IsDead("Heather") and heather):
        heather.ScriptUnhide()
    if((G.Heather_Gone or (G.Story_State >= 75 and G.Heather_Indoors == 0 and G.Player_Sabbat < 3)) and heather):
        heather.ScriptHide()
    if(G.Story_State >= 30 and G.Heather_Haven and not IsDead("Heather") and G.Heather_Gone == 0 and G.Story_State < 75 and not G.Heather_Lure):
        G.Mcfly_Present = 1
        mcfly = Find("McFly")
        if mcfly: mcfly.ScriptUnhide()
    if(G.Mcfly_Leave or G.Mcfly_Feed or G.Mcfly_Dominated or G.Mcfly_Dementated or IsDead("McFly")):
        mcfly = Find("McFly")
        if mcfly: mcfly.Kill()
    if(G.Heather_Clothes and heather):
        if (G.Gary_Haven):
            heatherSkin()
#        G.Heather_Outfit = G.Heather_Outfit + 1
#        if(G.Heather_Outfit > 2):
#            G.Heather_Outfit = 0
        G.Heather_Clothes = 0
    if(IsDead("Heather") and heather):
        heather.Kill()
        mcfly = Find("mcfly")
        if mcfly: mcfly.Kill()

#HAVEN: Called to see if Heather needs to leave the haven
def heatherLeaves():
    G = __main__.G
    if(G.Heather_Gone):
        relay = Find("heather_leaves_relay")
        relay.Trigger()

#HAVEN: Called to see if Mcfly leaves
def mcflyDialog():
    G = __main__.G
    if(G.Mcfly_Leave or G.Mcfly_Dominated or G.Mcfly_Dementated):
        relay = Find("mcfly_leaves_relay")
        relay.Trigger()

#HAVEN: Used for mailbox events for email quests at the haven, changed by wesp
def putStuffInMailBox():
    mailbox = Find("mailbox_haven")
    if mailbox:
        G = __main__.G
        if(G.Shubs_Email == 1 and G.Shubs_Email_Read < 1):
            mailbox.SpawnItemInContainer("item_k_shrekhub_one_key")
            G.Shubs_Email_Read = 1
        elif(G.Shubs_Email == 2 and G.Shubs_Email_Read < 2):
            mailbox.SpawnItemInContainer("item_g_wireless_camera_1")
            G.Shubs_Email_Read = 2
        elif(G.Shubs_Email == 3 and G.Shubs_Email_Read < 3):
            mailbox.SpawnItemInContainer("item_k_shrekhub_three_key")
            G.Shubs_Email_Read = 3
        elif(G.Shubs_Email == 4 and G.Shubs_Email_Read < 4):
            mailbox.SpawnItemInContainer("item_k_shrekhub_four_key")
            G.Shubs_Email_Read = 4
            
        #added by burgermeister 3/09
        #adds money to the mailbox for the Ventrue clan quest
        #also adds new blood to the fridge
        if(G.ventrue_quest_success == 1 and G.got_ventrue_reward < 1):
            cash = __main__.CreateEntityNoSpawn("item_m_money_envelope", (0, 0, 0), (0,0,0) )
            cash.SetName("ventrue_reward")
            cash.SetMoney(2000)
            __main__.CallEntitySpawn(cash)
            mailbox.AddEntityToContainer("ventrue_reward")
            
            fridge = Find("haven_refrigerator")
            if(not fridge): fridge = Find("fridge")
            
            if(fridge):
                fridge.SpawnItemInContainer("item_g_bluebloodpack")
                fridge.SpawnItemInContainer("item_g_eldervitaepack")
            
            G.got_ventrue_reward = 1
        if(G.Second_Hit_Complete == 1 and G.got_second_hit_reward < 1):
            cash = __main__.CreateEntityNoSpawn("item_m_money_envelope", (0, 0, 0), (0,0,0) )
            cash.SetName("hit_reward")
            cash.SetMoney(200)
            __main__.CallEntitySpawn(cash)
            mailbox.AddEntityToContainer("hit_reward")
            
            G.got_second_hit_reward = 1
        
        
        
        if(G.Third_Hit_Complete == 1 and G.got_third_hit_reward < 1):
            cash = __main__.CreateEntityNoSpawn("item_m_money_envelope", (0, 0, 0), (0,0,0) )
            cash.SetName("hit_reward")
            cash.SetMoney(200)
            __main__.CallEntitySpawn(cash)
            mailbox.AddEntityToContainer("hit_reward")               
            
            G.got_third_hit_reward = 1            

#HAVEN: Used to determine if the player has collected any posters, changed by wesp
def posterCheck():
    G = __main__.G
    cqm_fuhack.garyCallState()
    
    if(posters.isInstalled()):
        posters.posterCheck()
        return
        
    if(G.Gary_Voerman):
        poster = Find("poster_jeanette")
        poster.ScriptUnhide()
    if(G.Velvet_Poster):
        poster = Find("poster_vv")
        poster.ScriptUnhide()
    if(G.Gary_Photochop):
        poster = Find("poster_ming")
        poster.ScriptUnhide()
    if(G.Gary_Damsel):
        poster = Find("poster_damsel")
        poster.ScriptUnhide()
    if(G.Gary_Tawni):
        poster = Find("poster_tawni")
        poster.ScriptUnhide()
    if(G.Gary_Imalia):
        poster = Find("poster_imalia")
        poster.ScriptUnhide()
    if(G.Gary_Blind):
        poster = Find("poster_blind")
        poster.ScriptUnhide()
        if(G.Gary_Complete == 0):
            __main__.FindPlayer().SetQuest("Gary", 8)
            G.Gary_Complete = 1

#HAVEN: Updates the player's mailbox and flags if he has sent the blood in the mail, changed by wesp
def mailboxExitCheck():
    G = __main__.G
    container = Find("mailbox_haven")
    if container:
        if(G.Heather_Lure and G.Mcfly_Present and not (G.Mcfly_Leave or G.Mcfly_Feed or G.Mcfly_Dominated or G.Mcfly_Dementated)):
            G.Mcfly_Leave = 1
            pc = __main__.FindPlayer()
            pc.ChangeMasqueradeLevel(1)
            mcfly = Find("Mcfly")
            if mcfly: mcfly.Kill()
        if (container.HasItem("item_g_werewolf_bloodpack")):
            container.AddEntityToContainer("werewolf_reward")
            container.RemoveItem("item_g_werewolf_bloodpack")
            G.Werewolf_Quest = 4
            pc = __main__.FindPlayer()
            pc.SetQuest("Werewolf Blood", 3)
            pc.ChangeMasqueradeLevel(-1)
        if(container.HasItem("item_g_garys_film") and G.Story_State >= 45):
            container.RemoveItem("item_g_garys_film")
            G.Gary_Voerman = 1
        if(container.HasItem("item_g_garys_cd") and G.Gary_Voerman == 1 and G.Gary_Damsel == 0 and G.Patch_Plus == 0):
            container.RemoveItem("item_g_garys_cd")
            G.Gary_Damsel = 1
        if(container.HasItem("item_g_garys_tape") and G.Velvet_Poster == 1 and G.Gary_Photochop == 0 and G.Patch_Plus == 0):
            container.RemoveItem("item_g_garys_tape")
            G.Gary_Photochop = 1
        if(container.HasItem("item_g_garys_photo") and G.Gary_Damsel == 1 and G.Velvet_Poster == 0 and G.Patch_Plus == 0):
            container.RemoveItem("item_g_garys_photo")
            G.Velvet_Poster = 1
        if(container.HasItem("item_g_garys_cd") and G.Gary_Photochop == 1 and G.Gary_Damsel == 0 and G.Patch_Plus == 1):
            container.RemoveItem("item_g_garys_cd")
            G.Gary_Damsel = 1
        if(container.HasItem("item_g_garys_tape") and G.Velvet_Poster == 1 and G.Gary_Photochop == 0 and G.Patch_Plus == 1):
            container.RemoveItem("item_g_garys_tape")
            G.Gary_Photochop = 1
        if(container.HasItem("item_g_garys_photo") and G.Gary_Voerman == 1 and G.Velvet_Poster == 0 and G.Patch_Plus == 1):
            container.RemoveItem("item_g_garys_photo")
            G.Velvet_Poster = 1
            pc.ChangeMasqueradeLevel(-1)
        if(container.HasItem("item_g_wireless_camera_2") and G.Gary_Damsel == 1 and G.Gary_Tawni == 0):
            container.RemoveItem("item_g_wireless_camera_2")
            G.Gary_Tawni = 1
        if(container.HasItem("item_g_wireless_camera_3") and G.Gary_Tawni == 1 and G.Gary_Imalia == 0):
            container.RemoveItem("item_g_wireless_camera_3")
            G.Gary_Imalia = 1
        if(container.HasItem("item_g_wireless_camera_4") and G.Gary_Imalia == 1 and G.Gary_Blind == 0):
            container.RemoveItem("item_g_wireless_camera_4")
            G.Gary_Blind = 1
        if(container.HasItem("item_w_claws_protean4") and G.Gift_Email == 1 and G.Mitnick_Gift == 0):
            container.RemoveItem("item_w_claws_protean4")
            container.AddEntityToContainer("gift_reward")
            G.Mitnick_Gift = 1

#HAVEN: Updates the player's quest when he gets the email about werewolf blood
def werewolfBloodQuestAssigned():
    G = __main__.G
    if(G.Werewolf_Quest == 0):
        G.Werewolf_Quest = 1
        __main__.FindPlayer().SetQuest("Werewolf Blood", 1)
        achievements.assertAchievement(achievements.ACH_SM_QUESTS)        

#HAVEN: Updates the player's quest when he takes the reward for the werewolf blood
def werewolfBloodQuestDone():
    __main__.FindPlayer().SetQuest("Werewolf Blood", 4)

#HAVEN: Setting Quest State for Gift Quest, added by wesp
def mitSetQuest():
    __main__.FindPlayer().SetQuest("Gift", 1)

#HAVEN: Setting Quest State for Gift Quest, added by wesp
def mitSetQuestFinish():
    __main__.FindPlayer().SetQuest("Gift", 2)

#HAVEN: Setting Quest State Two for Mitnick Quest
def mitSetQuestTwo():
    __main__.FindPlayer().SetQuest("Mitnick", 2)

#HAVEN: Setting Quest State Three for Mitnick Quest
def mitSetQuestThree():
    __main__.FindPlayer().SetQuest("Mitnick", 3)

#HAVEN: Setting Quest State Four for Mitnick Quest
def mitSetQuestFour():
    __main__.FindPlayer().SetQuest("Mitnick", 4)

#HAVEN: Setting Quest State Five for Mitnick Quest
def mitSetQuestFive():
    __main__.FindPlayer().SetQuest("Mitnick", 5)

#HAVEN: Setting Quest State Six for Mitnick Quest
def mitSetQuestSix():
    __main__.FindPlayer().SetQuest("Mitnick", 6)

#HAVEN: Setting Quest State Seven for Mitnick Quest
def mitSetQuestSeven():
    __main__.FindPlayer().SetQuest("Mitnick", 7)

#HAVEN: Setting Quest State Eight for Mitnick Quest
def mitSetQuestEight():
    __main__.FindPlayer().SetQuest("Mitnick", 8)

#HAVEN: Setting Quest State Nine for Mitnick Quest, changed by wesp
def mitSetQuestNine():
    __main__.FindPlayer().SetQuest("Mitnick", 9)
    achievements.assertAchievement(achievements.ACH_MITNICK)
    achievements.assertAchievement(achievements.ACH_HW_QUESTS)    
    G.Shubs_Act = 4

#HAVEN: Setting Quest State One for Gary Quest, added by wesp
def garySetQuestOne():
    __main__.FindPlayer().SetQuest("Gary", 1)

#HAVEN: Setting Quest State Two for Gary Quest, added by wesp
def garySetQuestTwo():
    __main__.FindPlayer().SetQuest("Gary", 2)

#HAVEN: Setting Quest State Three for Gary Quest, added by wesp
def garySetQuestThree():
    __main__.FindPlayer().SetQuest("Gary", 3)

#HAVEN: Setting Quest State Four for Gary Quest, added by wesp
def garySetQuestFour():
    __main__.FindPlayer().SetQuest("Gary", 4)

#HAVEN: Setting Quest State Five for Gary Quest, added by wesp
def garySetQuestFive():
    __main__.FindPlayer().SetQuest("Gary", 5)

#HAVEN: Setting Quest State Six for Gary Quest, added by wesp
def garySetQuestSix():
    __main__.FindPlayer().SetQuest("Gary", 6)

#HAVEN: Setting Quest State Seven for Gary Quest, added by wesp
def garySetQuestSeven():
    __main__.FindPlayer().SetQuest("Gary", 7)

#HAVEN: Setting Quest State One for Bertram Quest, added by wesp
def bertramSetQuest():
    __main__.FindPlayer().SetQuest("BertramCD", 4)
    
#HAVEN:Setting Quest State For Malk Conspiracy Quest
def advanceMalkQuest():
    __main__.FindPlayer().SetQuest("conspire", 3)


#HAVEN: Email to start Ventrue clan quest    
def startVentrueQuest():
    __main__.FindPlayer().SetQuest("dirty",1)

#HAVEN: Email to end Ventrue clan quest    
def completeVentrueQuest():
    __main__.FindPlayer().SetQuest("dirty",5)


#HAVEN: Email for the hitman quest
def setHitmanQuest(stage):
    __main__.FindPlayer().SetQuest("kindredhire",stage)    

#HAVEN: Setting Quest State One for Tommy Quest
def tomSetQuest():
    __main__.FindPlayer().SetQuest("Tommy", 1)

#HAVEN:Setting Quest State Four for Tommy Quest, changes made by dan_upright 29/11/04
def tomSetQuestFour():
    __main__.FindPlayer().SetQuest("Tommy", 4)
    achievements.assertAchievement(achievements.ACH_HW_QUESTS)    
    container = Find("mailbox_haven")
    if container:
        cash = __main__.CreateEntityNoSpawn("item_m_money_envelope", (0, 0, 0), (0,0,0) )
        cash.SetName("critic_reward")
        cash.SetMoney(100)
        __main__.CallEntitySpawn(cash)
        container.AddEntityToContainer("critic_reward")
#changes end

#HAVEN: Called to cause the malk newscaster conversation
def malkTalkToTV():
    G = __main__.G
    pc = __main__.FindPlayer()
    if(IsClan(pc,"Malkavian") and G.Story_State >= 65 and G.News_Spoke == 0):
        newscaster = Find("newscaster")
        newscaster.ScriptHide()
        newscaster.SetName("newscaster_break")
        malkcaster = Find("newscaster_malkavian")
        malkcaster.ScriptUnhide()
        malkcaster.SetName("newscaster")
        trigger = Find("malk_tv_trigger")
        trigger.ScriptUnhide()

#HAVEN: Called after the malkavian talks to the TV
def malkTvDone():
    newscaster = Find("newscaster_break")
    malkcaster = Find("newscaster")
    malkcaster.Kill()
    newscaster.ScriptUnhide()
    newscaster.SetName("newscaster")

#HUBS: Sets a Global for the hub you are in should be on each hubs logic_auto
def setArea( s ):
    G = __main__.G
    G.In_Santa_Monica = 0
    G.In_Downtown = 0
    G.In_Hollywood = 0
    G.In_Chinatown = 0
    G.Whore_Follower = 0
    if ( s == "santa_monica" ):
        print ( "*** In Santa Monica ***" )
        G.In_Santa_Monica = 1
    elif ( s == "downtown" ):
        print ( "*** In Downtown ***" )
        G.In_Downtown = 1
    elif ( s == "hollywood" ):
        print ( "*** In Hollywood ***" )
        G.In_Hollywood = 1
    elif ( s == "chinatown" ):
        print ( "*** In Chinatown ***" )
        G.In_Chinatown = 1

#EMBRACE: Determines which models the sire and stakers should use.
def chooseSire():
    pc = __main__.FindPlayer()
    if(pc.HasItem("item_i_written")):
        pc.RemoveItem("item_i_written")
        __main__.G.Player_Homo = 1
    gender = pc.IsMale()
    clan = pc.clan
    sire = Find("Sire")
    staker1 = Find("Vampire1")
    staker2 = Find("Vampire2")
    brujah_female = "models/character/pc/female/brujah/armor3/brujah_female_armor_3.mdl"
    gangrel_female = "models/character/pc/female/gangrel/armor2/Gangrel_female_Armor_2.mdl"
    malkavian_female = "models/character/pc/female/malkavian/armor3/Malk_Girl_Armor_3.mdl"
    nosferatu_female = "models/character/pc/female/nosferatu/armor0/nosferatu_Female_Armor_0.mdl"
    toreador_female = "models/character/pc/female/toreador/armor2/toreador_female_armor_2.mdl"
    tremere_female = "models/character/pc/female/tremere/armor2/tremere_female_Armor_2.mdl"
    ventrue_female = "models/character/pc/female/ventrue/armor1/ventrue_female_Armor_1.mdl"
    brujah_male = "models/character/pc/male/brujah/armor0/brujah_Male_Armor_0.mdl"
    gangrel_male = "models/character/pc/male/gangrel/armor_2/Gangrel_Male_Armor_2.mdl"
    malkavian_male = "models/character/pc/male/malkavian/armor0/Malkavian_Male_Armor_0.mdl"
    nosferatu_male = "models/character/pc/male/nosferatu/armor0/Nosferatu.mdl"
    tremere_male = "models/character/pc/male/tremere/armor1/tremere_Male_armor_1.mdl"
    toreador_male = "models/character/pc/male/toreador/armor0/toreador_Male_Armor_0.mdl"
    ventrue_male = "models/character/pc/male/ventrue/armor1/ventrue_Male_Armor_1.mdl"
    #MALE
    if(gender):
        #BRUJAH
        if(clan == 2):
            sire.SetModel(brujah_female)
            staker1.SetModel(malkavian_male)
            staker2.SetModel(toreador_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(gangrel_male)
        #GANGREL
        elif(clan == 3):
            sire.SetModel(gangrel_female)
            staker1.SetModel(nosferatu_male)
            staker2.SetModel(tremere_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(brujah_male)
        #MALKAVIAN
        elif(clan == 4):
            sire.SetModel(malkavian_female)
            staker1.SetModel(toreador_male)
            staker2.SetModel(ventrue_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(toreador_male)
        #NOSFERATU
        elif(clan == 5):
            sire.SetModel(toreador_female)
            staker1.SetModel(tremere_male)
            staker2.SetModel(brujah_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(toreador_male)
        #TOREADOR
        elif(clan == 6):
            sire.SetModel(toreador_female)
            staker1.SetModel(ventrue_male)
            staker2.SetModel(gangrel_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(malkavian_male)
        #TREMERE
        elif(clan == 7):
            sire.SetModel(tremere_female)
            staker1.SetModel(brujah_male)
            staker2.SetModel(malkavian_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(ventrue_male)
        #VENTRUE
        elif(clan == 8):
            sire.SetModel(ventrue_female)
            staker1.SetModel(gangrel_male)
            staker2.SetModel(nosferatu_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(tremere_male)
    else:
        #BRUJAH
        if(clan == 2):
            sire.SetModel(brujah_male)
            staker1.SetModel(malkavian_male)
            staker2.SetModel(toreador_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(gangrel_female)
        #GANGREL
        elif(clan == 3):
            sire.SetModel(gangrel_male)
            staker1.SetModel(nosferatu_male)
            staker2.SetModel(tremere_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(brujah_female)
        #MALKAVIAN
        elif(clan == 4):
            sire.SetModel(malkavian_male)
            staker1.SetModel(toreador_male)
            staker2.SetModel(ventrue_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(toreador_female)
        #NOSFERATU
        elif(clan == 5):
            sire.SetModel(toreador_male)
            staker1.SetModel(tremere_male)
            staker2.SetModel(brujah_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(toreador_female)
        #TOREADOR
        elif(clan == 6):
            sire.SetModel(toreador_male)
            staker1.SetModel(ventrue_male)
            staker2.SetModel(gangrel_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(malkavian_female)
        #TREMERE
        elif(clan == 7):
            sire.SetModel(tremere_male)
            staker1.SetModel(brujah_male)
            staker2.SetModel(malkavian_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(ventrue_female)
        #VENTRUE
        elif(clan == 8):
            sire.SetModel(ventrue_male)
            staker1.SetModel(gangrel_male)
            staker2.SetModel(nosferatu_male)
            if __main__.G.Player_Homo == 1:
                sire.SetModel(tremere_female)
    #FINISH THIS FUNCTION

#PROSTITUTES: Called when initiating dialogue with a prostitute to change her name to "prostitute"
#              MUST BE CALLED AS THE DIALOG SCRIPT and pass in the original name of the prositute (prostitute_x)
def changeProstituteName(name):
    print "change name from %s" % name
    G = __main__.G
    G.Prostitute_Name = name
    hooker = Find(name)
    hooker.SetName("prostitute")
    return 0

#PROSTITUTES: Disband and feed (dialogue)
def disbandFeed():
    G = __main__.G
    print ( "*************** Disband and Feed ***************" )
    __main__.npc.SetFollowerBoss( "" )
    __main__.pc.SeductiveFeed( __main__.npc )
    G.In_Alley = 0
    resetHos()

#PROSTITUTES: Prostitute make whore your ho (from dlg)
def makeFollower():
    print ( "*************** Make Follower ***************" )
    __main__.npc.SetFollowerBoss( "!player" )

#PROSTITUTES: Causes prostitutes to flee(on events_world for each hub), fixed by RobinHood70
def fleeingHos():
    print ( "*************** Prostitute Flees Check ***************" )
    pc = __main__.FindPlayer()
    prostitutes = FindList("prostitut*")
    for prostitute in prostitutes:
        if(prostitute.classname != "filter_activator_name"):
            if prostitute.IsFollowerOf(pc):
                print ( "*************** Prostitute Flees ***************" )
                G = __main__.G
                G.Whore_Follower = 0
                if ( G.Romero_Whore == 2 ):
                    G.Romero_Whore = 1
                prostitute.SetFollowerBoss("")
                prostitute.SetRelationship("player D_FR 5")

#PROSTITUTES: Reset Hos, needs to be put on all trigger_change_levels on each hub, fixed by RobinHood70
def resetHos():
    G = __main__.G
    prostitutes = FindList("prostitut*")
    for prostitute in prostitutes:
        if(prostitute.classname != "filter_activator_name"): prostitute.SetFollowerBoss("")
    G.Whore_Follower = 0
    if (G.Romero_Whore == 2):
        G.Romero_Whore = 1

#PROSTITUTES: Revert's hooker's name at end of dialogue
def revertHookerName():
    G = __main__.G
    print "change name to %s" % G.Prostitute_Name
    hooker = Find("prostitute")
    hooker.SetName(G.Prostitute_Name)

#PROSTITUTES: Prostitute Inits Dialogue (on alley triggers), fixed by RobinHood70
def prostituteInit():
    G = __main__.G
    print ( "*************** Check if Prostitue is Follower ***************" )
    if (G.Romero_Whore == 2):
        return
    if (G.Whore_Follower == 1):
        pc = __main__.FindPlayer()
        G.In_Alley = 1
        prostitutes = FindList("prostitut*")
        for prostitute in prostitutes:
            if(prostitute.classname != "filter_activator_name"):
                if (prostitute.IsFollowerOf( pc )):
                    prostitute.StartPlayerDialog(0)
                    
def q(name,num):
    __main__.FindPlayer().SetQuest(name,num)                    

#Refills ammo for the guns the PC has
def masterRefill(param):
    paramlist = param.split()
    quantity = atoi(paramlist[1])
    container = Find( paramlist[0] )
    player = __main__.FindPlayer()
    gotammo = 0
    chance = 0
    if container:
        print ( "****************** Found Container ********************" )
        container.DeleteItems()
        if ( player.HasItem("item_w_colt_anaconda") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Anaconda Ammo ********************" )
                container.SpawnItemInContainer("item_w_colt_anaconda")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_crossbow") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Bolts ********************" )
                container.SpawnItemInContainer("item_w_crossbow")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_crossbow_flaming") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Fire Bolts ********************" )
                container.SpawnItemInContainer("item_w_crossbow_flaming")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_deserteagle") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Deagle Clip ********************" )
                container.SpawnItemInContainer("item_w_deserteagle")
                quantityv = quantityv - 1
#        if ( player.HasItem("item_w_flamethrower") ):
#            quantityv = quantity
#            gotammo = 1
#            while (quantityv > 0):
#                print ( "****************** Flamethrower Fuel ********************" )
#                container.SpawnItemInContainer("item_w_flamethrower")
#                quantityv = quantityv - 1
        if ( player.HasItem("item_w_glock_17c") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Glock Clip ********************" )
                container.SpawnItemInContainer("item_w_glock_17c")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_ithaca_m_37") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Shotgun Shells ********************" )
                container.SpawnItemInContainer("item_w_ithaca_m_37")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_mac_10") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Mac-10 Clip ********************" )
                container.SpawnItemInContainer("item_w_mac_10")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_rem_m_700_bach") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Bach Ammo ********************" )
                container.SpawnItemInContainer("item_w_rem_m_700_bach")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_remington_m_700") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Remington Ammo ********************" )
                container.SpawnItemInContainer("item_w_remington_m_700")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_steyr_aug") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Steyr-Aug Clip ********************" )
                container.SpawnItemInContainer("item_w_steyr_aug")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_supershotgun") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Shotgun Clip ********************" )
                container.SpawnItemInContainer("item_w_supershotgun")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_thirtyeight") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** .38 Rounds ********************" )
                container.SpawnItemInContainer("item_w_thirtyeight")
                quantityv = quantityv - 1
        if ( player.HasItem("item_w_uzi") ):
            quantityv = quantity
            gotammo = 1
            while (quantityv > 0):
                print ( "****************** Uzi Clip ********************" )
                container.SpawnItemInContainer("item_w_uzi")
                quantityv = quantityv - 1
        if ( gotammo == 1 ):
            print ( "****************** Filled Container ********************" )
            return
        else:
            print ( "****************** PC has no Guns ********************")
            R = Random( time() )
            chance = R.randint (1, 3)
            if ( chance == 1 or chance == 2 ):
                print ( "****************** Cheap Watch ********************" )
                container.SpawnItemInContainer("item_g_watch_normal")
            if ( chance == 3 ):
                print ( "****************** Nice Watch ********************" )
                container.SpawnItemInContainer("item_g_watch_fancy")
    else:
        print ( "****************** No Container ********************" )

##############################################################################
# Classes
##############################################################################

#CQM: Added by burgermeister
# This function handles the scenario in which Steve, the corrupt CDC worker, is killed
# This is in vamputil, because Steve can appear in one of two maps.
def steveKilled():
    state =__main__.FindPlayer().GetQuestState("poison")
    if(state > 0 and state < 6):
        __main__.FindPlayer().SetQuest("poison",7)
        
        
def isCompInstalled():
    use_context_loads = fileutil.getcwd() + "\\CQM\\cfg\\comp.cfg"
    
    if(not fileutil.exists(use_context_loads)):       
        return 0
    
    else:
        __main__.G.Comp = 1
        return 1      
        
def isCEInstalled():        
    use_ce = fileutil.getcwd() + "\\CQM\\cfg\\ce.cfg"
    
    if(not fileutil.exists(use_ce)):       
        return 0    
    else:
        __main__.G.CE = 1
        return 1

def isBloodTimerOn():
    root = fileutil.getcwd()
    file_path = root + "\\CQM\\cfg\\ce.cfg"
    data = ""
    
    if(fileutil.exists(file_path)):
        data = fileutil.readlines(file_path,1)[0]
        value = data.split('=')
        
        if(value[0] == "bloodloss" and value[1]=="1"):
            return 1
        
    return 0        
        
#This function will toggle the loading screen based on game state       
def SwitchScreens():
    
    #First check to see if the cfg file for this loading screen mod is installed
    #If not just skip it all
    use_context_loads = fileutil.getcwd() + "\\CQM\\cfg\\context_load.cfg"
    
    if(not fileutil.exists(use_context_loads)):       
        return
        
    
    state = __main__.G.Story_State
    
    #If this is a new game, initialize the last story state
    #as 0.Even if the player is in the tutorial, this is fine
    #as the script doesn't account for story states, before
    #0 and just defaults to the zero-index loading screen
    if(not __main__.G.Last_Story_State):
        __main__.G.Last_Story_State = 0
    
    last_state = __main__.G.Last_Story_State
    
    #If there's been no change in the story state, skip all the 
    #file operations
    if(state == last_state):
        return
    
    
    
    #Declare relevant directory, file names
    dir = fileutil.getcwd() + "\\CQM\\materials\\interface\\tipinfoscreen\\"
    live_file_name = "background_default"
    
    main_tth_file =  dir + live_file_name + ".tth" 
    main_ttz_file =  dir + live_file_name + ".ttz"
    
    
    #This defines the games states at which we should switch screens
    game_states = [[0,10], [10,35], [35, 45], [45, 60], [60, 150]]
    
    
    #This defines the extensions we look for, which correspond to the above game states
    file_extensions = ["_1", "_2", "_3", "_4", "_5"]
    i = 0
    
    
    #Loop through each of the possible loading screens.
    for extension in file_extensions:

	
        this_ttz_file = dir + live_file_name + ".ttz" + extension
        
        #If a particular loading screen is missing, then we know that the missing screen
        #is the one being currently used.
        if(not fileutil.exists(this_ttz_file)):
                   
            this_tth_file = dir + live_file_name + ".tth" + extension
            
	    
	    #Copy the current loading screen into the one which would otherwise be missing
            fileutil.copyfile(main_tth_file, this_tth_file)
            fileutil.copyfile(main_ttz_file, this_ttz_file)
            
            
            
            j = 0
            idx = 0
            #Loop through each of the possible game state brackets and pick the one which applies
            #to the player's current situation
            for state_set in game_states:
                if(state >= state_set[0] and state < state_set[1]):
                    idx = j
                    break
                
                j += 1
            

            #Copy the corresponding, correct loading screen as the current loading screen
            fileutil.copyfile(dir + live_file_name + ".tth" + file_extensions[idx], main_tth_file)
            fileutil.copyfile(dir + live_file_name + ".ttz" + file_extensions[idx], main_ttz_file)
            
            #Remove the source file copied INTO the loading screen, so as to later indicate
            #that it is the "current" loading screen
            fileutil.removefile(dir + live_file_name + ".tth" + file_extensions[idx])
            fileutil.removefile(dir + live_file_name + ".ttz" + file_extensions[idx])
            
            try:
                __main__.ccmd.mat_reloadtextures()
            except:
                pass
            
            __main__.G.Last_Story_State = state
            
            return
            
            
        i += 1
        
        
        
def hitmanHumanity():
    ChangeHumanity( -1,3 )
    
    
#Toggle walking/running, added by wesp
def toggleSpeed():
    G = __main__.G
    c = __main__.ccmd
    if(G.Walk == 1):
        c.run=""
        G.Walk = 0
    else:
        c.walk=""
        G.Walk = 1

#Toggle automatic moving, added by wesp
def toggleMove():
    G = __main__.G
    c = __main__.ccmd
    if(G.Go == 1):
        c.stop=""
        G.Go = 0
    else:
        c.go=""
        G.Go = 1    
    
    
    
def leaveCamarilla():

    failQuest("Werewolf Blood", (1,2,3), 5)
    failQuest("Strauss", (1,20), 3)
    failQuest("BertramCD", (1,2,4), 5)
#    failQuest("Plague", (1,2,3,4,5,6,7,8,11,12,13,14,15), 16)
#    failQuest("AllPlague", (1,2,3,6,7,8,9,10,11,12,13), 14)
    failQuest("Junky", (1,2,5,6,7), 9)
    failQuest("Regent", (1,2,3,4,5,8), 9)
    failQuest("Sarcophagus", (1,2,3,5), 6)
    failQuest("Bmagic", (1,6), 8)
    failQuest("madness", (1,2,3,4,5,6), 9)
    failQuest("dirty", (1,2,3,4), 11)
    failQuest("Gargoyle", (1,2,3,4,6,7,9), 10)
    failQuest("Tommy", (1,2), 5)
    failQuest("Imalia", (1,2,3,4), 9)
    failQuest("Guy", (1,2), 6)
    failQuest("Mitnick", (1,25), 11)
    failQuest("favors", (1,2,3,4,5,6,7,15,16), 17)
    failQuest("Kings Way", (1,1), 5)
    failQuest("Strip", (1,2), 5)
    
    laptop = __main__.Find("garys_laptop")
    
    if(laptop):
        laptop.Enable()
        
    __main__.G.Gary_Hostile=2
    __main__.G.Player_Sabbat=1
    __main__.FindPlayer().SetQuest("betray",2)
    
    
    __main__.G.Werewolf_Quest=0
    __main__.G.Imalia_Guymag=0
    __main__.G.Mitnick_Quest=0
    __main__.G.Skelter_Quest=0
    __main__.G.Damsel_Quest=0
    __main__.G.TinCanBill_Know=0
    __main__.G.TinCanBill_Nos=0
    __main__.G.CompHaven="sm_pawnshop_1"
    
    ents = ["Imalia", "Mitnick","item_g_bertrams_cd"]
    
    for ent in ents:
        e = __main__.Find(ent)
        if(e):
            e.Kill()


def failQuest(quest_name, states, new_state):
    current_state = __main__.FindPlayer().GetQuestState(quest_name)
    if(current_state in states):
        __main__.FindPlayer().SetQuest(quest_name, new_state)
        
def johansenQuest(state):
    quest="Johansen"
    if(__main__.G.Player_Sabbat == 1):
        quest="Prof_Hunting"
    print quest
    __main__.FindPlayer().SetQuest(quest,state)
    
def setBarabusQuest(state):
    quest = "Barabus"
    if(__main__.G.Player_Sabbat == 1):
        quest = "Mack_Nos"
    
    __main__.FindPlayer().SetQuest(quest,state)
    
    
def MingXiaoBarabus(state):
    if(not __main__.G.Player_Sabbat == 1):
        __main__.FindPlayer().SetQuest("Barabus", state)
    
    
def switchEastLA(src):
    
    if(src == "sewer"):
        __main__.G.Sewer_EastLA = 1

    if(__main__.Find("taxi_eastla_downtown_marker")):
        marker = "taxi_eastla_downtown_marker"
        trigger = "taxi_eastla_downtown"
    elif(__main__.Find("taxi_eastla_hollywood_marker")):
        marker = "taxi_eastla_hollywood_marker"
        trigger = "taxi_eastla_hollywood"
    elif(__main__.Find("taxi_eastla_santa_monica_marker")):
        marker = "taxi_eastla_santa_monica_marker"
        trigger = "taxi_eastla_santa_monica"
    elif(__main__.Find("taxi_eastla_chinatown_marker")):
        marker = "taxi_eastla_chinatown_marker"
        trigger = "taxi_eastla_chinatown"
        

    if(marker and trigger):        
        __main__.ChangeMap(2.5, marker, trigger)

            
def leaveEastLA(src, map):
    marker = "taxi_eastla_" + map + "_marker"
    trigger = "taxi_eastla_" + map

    if(marker and trigger):
        __main__.ChangeMap(2.5, marker, trigger)
        
    if(src == "sewer"):
        __main__.G.Sewer_EastLA = 1
        
def isEastLA():

    status = 0
    if(__main__.Find("eastla_detect")):
        status = 1
    
    return status
        
def eastLASewerArrive():
    
    if(__main__.G.Sewer_EastLA == 1):
        __main__.G.Sewer_EastLA=0
                 
        target = __main__.Find("sewer_eastla_arrive")
        if(target):
            __main__.FindPlayer().SetOrigin(target.GetOrigin())
            
def enableEastLANavigation():
    button = __main__.Find("eastla_button")
    inspect = __main__.Find("eastla_nav_hint")
    
    if(__main__.G.EastLA_Open == 1 and __main__.IsClan(__main__.FindPlayer(), "Nosferatu")):
        if(button):
            button.ScriptUnhide()
        if(inspect):
            inspect.ScriptUnhide()
            inspect.TurnOn()

def noEastLAMap():
    if(not __main__.IsClan(__main__.FindPlayer(), "Nosferatu")):
        __main__.Find("sewer_map").Lock()
                        
    
def spawnProp(parent_ent, suffix):
    _EntCreate = __main__.CreateEntityNoSpawn
    _EntSpawn  = __main__.CallEntitySpawn
    e=_EntCreate ("prop_dynamic", parent_ent.GetOrigin(),parent_ent.GetAngles())
    e.SetName("prop_" + suffix)
    e.SetModel(parent_ent.GetModelName())
    _EntSpawn(e)
    
    
def ex(npc, ex, time, extent=1):
    if(ex == "an"):
        ex = "Anger"
    elif (ex == "j"):
        ex = "Joy"
    elif (ex == "s"):
        ex = "Sad"
    elif(ex == "f"):
        ex = "Fear"
    elif (ex == "fl"):
        ex = "Flirtatious"
    elif (ex == "c"):
        ex = "Confused"
    elif (ex == "ap"):
        ex = "Apathy"
    elif (ex == "n"):
        ex = "Neutral"
    else:
        ex = "Neutral"
    name = npc.GetName()
    __main__.ScheduleTask(time, "__main__.Find(\"" + name + "\").SetDisposition(\"" + ex + "\", " + str(extent) + ")")
    
def moveEnt(base_ent, move_ent, x,y,z):
    if(base_ent):
        origin = base_ent.GetOrigin()
        xx = origin[0]+x
        yy = origin[1]+y
        zz = origin[2]+z
        new_origin = (xx,yy,zz)
        move_ent.SetOrigin(new_origin)
    
def toggleSeriesEntities(ents, state):
    if(state == "hide"):
        for ent in ents:
            if(ent):
                ent.ScriptHide()
    elif(state == "show"):
        for ent in ents:            
            if(ent):
                ent.ScriptUnhide()

def killEntity(ent_name):
    ent = __main__.Find(ent_name)
    if(ent):
        ent.Kill()
        
def protectFighter(name):

    ent = __main__.Find(name)
    if(ent):
        ent.MakeInvincible(1)

def hasHeather():
    r = 0
    if(isCompInstalled()):
        c1 = __main__.Find("companion1")
        c2 = __main__.Find("companion2")
        hkey = "models/character/npc/unique/santa_monica/heather"
        if( (c1 and c1.GetID() == hkey) or (c2 and c2.GetID() == hkey) ):
            r = 1            
    return r   
    
    
    
def sabbatFriendsUnset():

    __main__.G.Arturo_Mission=0
    __main__.G.Victoria_Mission=0
    __main__.G.Arianna_Mission=0
    __main__.G.Hazel_Mission=0
    __main__.G.Reset_Friends_Talk=1
    comp1= __main__.Find("companion1")
    comp2 = __main__.Find("companion2")
    comp3 = __main__.Find("companion3")
    
    if(comp1):
        key = comp1.GetID()
        companion.removeHenchmanHelper(comp1,1,0)        
#        companion.removeFromPartyHelper(comp1)
        del __main__.G.complist[__main__.G.complist.index(key)]
    if(comp2):
        key = comp2.GetID()
        companion.removeHenchmanHelper(comp2,1,0)
#        companion.removeFromPartyHelper(comp2)
        del __main__.G.complist[__main__.G.complist.index(key)]
    if(comp3):
        key = comp3.GetID()
        companion.removeHenchmanHelper(comp3,1,0)
#        companion.removeFromPartyHelper(comp3)
        del __main__.G.complist[__main__.G.complist.index(key)]
     
    #companion.clearCompanions()
    #companion.ResetCompanions()

    
def ChangeHumanity(change, level):
    diablorie.ChangeHumanity(change, level)
        
#This is here because in the haven_pc file (or any of the hackterminals for that matter), there is an upper limit on
#the number of characters that can appear in the dependency statement for an email of 64. Because some of these
#conditions are so long, dependency statement then they need to be routed through this function instead
    
def testEmail(name):
    if(name == "tommyReviewBad"):
        return (__main__.G.Tommy_Disgusted == 1 or __main__.G.Tommy_Review == 1) and __main__.G.Player_Sabbat==0
    
    if(name == "VVSecond"):
        return __main__.G.Velvet_Email == 1 and __main__.G.Story_State >= 60 and __main__.G.Player_Sabbat==0
    
    if(name == "JeanetteBored"):
        return __main__.G.Story_State >= 30 and __main__.G.Therese_Dead == 1 and __main__.G.Player_Sabbat==0
    
    if(name == "tommyDead"):
        return __main__.G.Tommy_Review == 2 and __main__.G.Story_State >= 150 and __main__.G.Player_Sabbat==0       
            
    if(name == "beckettLibrary"):
        if(__main__.G.Patch_Plus == 0):
            return 0
        else:
            return __main__.G.Jumbles_Removed==1 and __main__.G.LaSombra_Seen==1 and __main__.G.Player_Sabbat==0            
            
    if(name == "beckettLibraryComplete"):
        if(__main__.G.Patch_Plus == 0):
            return 0
        else:
            return __main__.G.Jumbles_Removed==2 and __main__.G.Player_Sabbat==0            
        
    if(name == "bertramCDQuest"):
        return __main__.G.CD_Quest==1 and __main__.FindPlayer().clan==5 and __main__.G.Player_Sabbat==0
        
    if (name == "VVThird"):
        return __main__.G.Velvet_Email == 1 and __main__.G.Story_State >= 70 and __main__.G.Player_Sabbat==0
        
    if(name == "ventrueCQMStart"):
        return __main__.G.Story_State>=25 and __main__.FindPlayer().clan==8 and __main__.G.Player_Sabbat==0
    
    if(name == "ventrueCQMSuccess"):
        return __main__.G.ventrue_quest_success == 1 and not __main__.G.hitman_dead == 1 and __main__.G.Player_Sabbat==0
        
    if(name == "ventrueCQMSuccessKillHitman"):
        return __main__.G.ventrue_quest_success == 1 and __main__.G.hitman_dead == 1 and __main__.G.Player_Sabbat==0

