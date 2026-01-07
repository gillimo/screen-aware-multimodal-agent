package com.osrscoach;

import com.google.inject.Provides;
import javax.inject.Inject;
import net.runelite.api.Client;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.swing.SwingUtilities;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.command.CommandManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import net.runelite.client.ui.overlay.OverlayManager;

@PluginDescriptor(
    name = "AgentOSRS",
    description = "Local coaching overlay for plan/ratings/blockers",
    tags = {"coach", "plan", "overlay"}
)
public class OsrsCoachPlugin extends Plugin
{
    private static final String COACH_ROOT = System.getProperty("user.home")
        + "\\OneDrive\\Desktop\\projects\\agentosrs";
    private static final Path STATE_PATH = Path.of(COACH_ROOT, "data", "state.json");
    private static final Gson GSON = new Gson();

    @Inject
    private Client client;

    @Inject
    private OverlayManager overlayManager;

    @Inject
    private OsrsCoachOverlay overlay;

    @Inject
    private CommandManager commandManager;

    @Provides
    OsrsCoachConfig provideConfig(ConfigManager configManager)
    {
        return configManager.getConfig(OsrsCoachConfig.class);
    }

    @Override
    protected void startUp()
    {
        overlayManager.add(overlay);
        commandManager.registerCommand(
            "coachreload",
            (args) -> overlay.setStatus("Reloaded at " + System.currentTimeMillis()),
            "Reload AgentOSRS overlay data"
        );
        commandManager.registerCommand(
            "coachui",
            (args) -> launchTkUi(),
            "Launch AgentOSRS desktop UI"
        );
    }

    @Override
    protected void shutDown()
    {
        commandManager.unregisterCommand("coachreload");
        commandManager.unregisterCommand("coachui");
        overlayManager.remove(overlay);
    }

    @Subscribe
    public void onGameStateChanged(net.runelite.api.events.GameStateChanged event)
    {
        if (event.getGameState() == GameState.LOGGED_IN)
        {
            Player player = client.getLocalPlayer();
            if (player != null && player.getName() != null)
            {
                String name = player.getName();
                overlay.setAccountName(name);
                syncAccountName(name);
            }
        }
    }

    private void syncAccountName(String name)
    {
        try
        {
            if (!Files.exists(STATE_PATH))
            {
                return;
            }
            String raw = Files.readString(STATE_PATH);
            JsonObject root = GSON.fromJson(raw, JsonObject.class);
            if (root == null)
            {
                return;
            }
            JsonObject account = root.has("account") ? root.getAsJsonObject("account") : new JsonObject();
            account.addProperty("name", name);
            root.add("account", account);
            Files.writeString(STATE_PATH, GSON.toJson(root));
        }
        catch (IOException ignored)
        {
        }
    }

    private void launchTkUi()
    {
        SwingUtilities.invokeLater(() -> {
            try
            {
                new ProcessBuilder("python", "run_coach.py", "gui")
                    .directory(Path.of(COACH_ROOT).toFile())
                    .start();
            }
            catch (IOException ignored)
            {
            }
        });
    }
}

