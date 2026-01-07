package com.sessionstats;

import com.google.inject.Provides;
import javax.inject.Inject;
import net.runelite.api.Client;
import net.runelite.api.NPC;
import net.runelite.api.Item;
import net.runelite.api.ItemContainer;
import net.runelite.api.InventoryID;
import net.runelite.api.Perspective;
import net.runelite.api.Point;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.events.GameTick;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import java.util.List;

@PluginDescriptor(
    name = "Session Stats",
    description = "Track session statistics and export play data",
    tags = {"stats", "session", "xp", "tracker"}
)
public class SessionStatsPlugin extends Plugin
{
    private static final Path EXPORT_PATH = Path.of(
        System.getProperty("user.home"), ".runelite", "session_stats.json"
    );
    private static final Gson GSON = new GsonBuilder().create();

    private int tickCounter = 0;
    private static final int EXPORT_INTERVAL = 2;

    @Inject
    private Client client;

    @Provides
    SessionStatsConfig provideConfig(ConfigManager configManager)
    {
        return configManager.getConfig(SessionStatsConfig.class);
    }

    @Override
    protected void startUp() {}

    @Override
    protected void shutDown() {}

    @Subscribe
    public void onGameTick(GameTick event)
    {
        tickCounter++;
        if (tickCounter >= EXPORT_INTERVAL)
        {
            tickCounter = 0;
            exportData();
        }
    }

    private void exportData()
    {
        if (client.getGameState() != GameState.LOGGED_IN) return;

        try
        {
            JsonObject data = new JsonObject();
            data.addProperty("t", System.currentTimeMillis());
            data.addProperty("tick", client.getTickCount());

            Player p = client.getLocalPlayer();
            if (p != null)
            {
                JsonObject pd = new JsonObject();
                WorldPoint wp = p.getWorldLocation();
                if (wp != null)
                {
                    pd.addProperty("wx", wp.getX());
                    pd.addProperty("wy", wp.getY());
                    pd.addProperty("wz", wp.getPlane());
                }
                LocalPoint lp = p.getLocalLocation();
                if (lp != null)
                {
                    Point sp = Perspective.localToCanvas(client, lp, client.getPlane());
                    if (sp != null)
                    {
                        pd.addProperty("sx", sp.getX());
                        pd.addProperty("sy", sp.getY());
                    }
                }
                pd.addProperty("a", p.getAnimation());
                data.add("p", pd);
            }

            JsonObject cam = new JsonObject();
            cam.addProperty("y", client.getCameraYaw());
            cam.addProperty("p", client.getCameraPitch());
            data.add("c", cam);

            JsonArray npcs = new JsonArray();
            List<NPC> npcList = client.getNpcs();
            Player localPlayer = client.getLocalPlayer();
            WorldPoint playerWorld = localPlayer != null ? localPlayer.getWorldLocation() : null;

            if (npcList != null && playerWorld != null)
            {
                for (NPC npc : npcList)
                {
                    if (npc == null) continue;
                    WorldPoint nw = npc.getWorldLocation();
                    if (nw == null) continue;
                    if (playerWorld.distanceTo(nw) > 15) continue;

                    JsonObject nd = new JsonObject();
                    nd.addProperty("id", npc.getId());
                    String name = npc.getName();
                    if (name != null) nd.addProperty("n", name);
                    nd.addProperty("wx", nw.getX());
                    nd.addProperty("wy", nw.getY());

                    LocalPoint nl = npc.getLocalLocation();
                    if (nl != null)
                    {
                        Point sp = Perspective.localToCanvas(client, nl, client.getPlane());
                        if (sp != null)
                        {
                            nd.addProperty("sx", sp.getX());
                            nd.addProperty("sy", sp.getY());
                            nd.addProperty("v", true);
                        }
                    }
                    npcs.add(nd);
                }
            }
            data.add("npcs", npcs);

            JsonArray inv = new JsonArray();
            ItemContainer ic = client.getItemContainer(InventoryID.INVENTORY);
            if (ic != null)
            {
                Item[] items = ic.getItems();
                for (int i = 0; i < items.length && i < 28; i++)
                {
                    if (items[i].getId() != -1)
                    {
                        JsonObject it = new JsonObject();
                        it.addProperty("s", i);
                        it.addProperty("id", items[i].getId());
                        it.addProperty("q", items[i].getQuantity());
                        inv.add(it);
                    }
                }
            }
            data.add("inv", inv);

            JsonObject skills = new JsonObject();
            for (Skill skill : Skill.values())
            {
                if (skill == Skill.OVERALL) continue;
                skills.addProperty(skill.getName().substring(0, 3).toLowerCase(),
                    client.getRealSkillLevel(skill));
            }
            data.add("sk", skills);

            data.addProperty("tp", client.getVarbitValue(281));

            Files.writeString(EXPORT_PATH, GSON.toJson(data));
        }
        catch (Exception e) {}
    }
}
