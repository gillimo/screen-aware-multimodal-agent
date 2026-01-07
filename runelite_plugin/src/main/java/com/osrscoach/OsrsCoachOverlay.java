package com.osrscoach;

import java.awt.Dimension;
import java.awt.Graphics2D;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import javax.inject.Inject;
import net.runelite.client.ui.overlay.Overlay;
import net.runelite.client.ui.overlay.OverlayLayer;
import net.runelite.client.ui.overlay.OverlayPosition;
import net.runelite.client.ui.overlay.components.LineComponent;
import net.runelite.client.ui.overlay.components.PanelComponent;

public class OsrsCoachOverlay extends Overlay
{
    private final OsrsCoachConfig config;
    private final PanelComponent panel = new PanelComponent();
    private String status = "";
    private String accountName = "";

    @Inject
    public OsrsCoachOverlay(OsrsCoachConfig config)
    {
        this.config = config;
        setPosition(OverlayPosition.TOP_LEFT);
        setLayer(OverlayLayer.UNDER_WIDGETS);
    }

    @Override
    public Dimension render(Graphics2D graphics)
    {
        panel.getChildren().clear();
        String header = accountName.isEmpty() ? "AgentOSRS" : "AgentOSRS (" + accountName + ")";
        panel.getChildren().add(LineComponent.builder().left(header).build());
        if (!status.isEmpty())
        {
            panel.getChildren().add(LineComponent.builder().left(status).build());
        }

        List<String> lines = readLines();
        for (String line : lines)
        {
            panel.getChildren().add(LineComponent.builder().left(line).build());
        }
        return panel.render(graphics);
    }

    private List<String> readLines()
    {
        List<String> lines = new ArrayList<>();
        Path path = Path.of(System.getProperty("user.home"), "OneDrive", "Desktop", "projects", "agentosrs", "data", "overlay.txt");
        try
        {
            if (Files.exists(path))
            {
                lines = Files.readAllLines(path);
            }
        }
        catch (Exception e)
        {
            lines.add("overlay.txt not readable");
        }
        return lines;
    }

    public void setStatus(String status)
    {
        this.status = status;
    }

    public void setAccountName(String accountName)
    {
        this.accountName = accountName;
    }
}

