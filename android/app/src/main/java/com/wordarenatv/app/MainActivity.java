package com.wordarenatv.app;

import android.app.Activity;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {

    private static final int DISCOVERY_PORT = 41234;
    private static final String DISCOVERY_MESSAGE = "WORD_ARENA_TV_DISCOVER";

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        setContentView(webView);

        webView.loadUrl("file:///android_asset/admin.html");
    }

    private class AndroidBridge {
        @JavascriptInterface
        public void discover() {
            new Thread(MainActivity.this::runDiscovery).start();
        }
    }

    private void runDiscovery() {
        DatagramSocket socket = null;
        try {
            socket = new DatagramSocket();
            socket.setBroadcast(true);
            socket.setSoTimeout(4000);

            byte[] outData = DISCOVERY_MESSAGE.getBytes("UTF-8");
            for (InetAddress target : broadcastTargets()) {
                try {
                    socket.send(new DatagramPacket(outData, outData.length, target, DISCOVERY_PORT));
                } catch (Exception ignored) {
                    // one target failing (e.g. no route) should not stop the others
                }
            }

            byte[] inBuffer = new byte[512];
            DatagramPacket inPacket = new DatagramPacket(inBuffer, inBuffer.length);
            socket.receive(inPacket);

            String serverIp = inPacket.getAddress().getHostAddress();
            String json = new String(inPacket.getData(), 0, inPacket.getLength(), "UTF-8");
            int port = extractPort(json);

            notifyFound(serverIp, port);
        } catch (Exception e) {
            notifyNotFound();
        } finally {
            if (socket != null) socket.close();
        }
    }

    private List<InetAddress> broadcastTargets() {
        List<InetAddress> list = new ArrayList<>();
        try {
            WifiManager wifi = (WifiManager) getApplicationContext().getSystemService(WIFI_SERVICE);
            if (wifi != null) {
                int ip = wifi.getDhcpInfo().ipAddress;
                int mask = wifi.getDhcpInfo().netmask;
                if (ip != 0 && mask != 0) {
                    int broadcast = (ip & mask) | ~mask;
                    byte[] quads = new byte[4];
                    for (int k = 0; k < 4; k++) {
                        quads[k] = (byte) ((broadcast >> (k * 8)) & 0xFF);
                    }
                    list.add(InetAddress.getByAddress(quads));
                }
            }
        } catch (Exception ignored) {
            // fall through to the generic broadcast address below
        }
        try {
            list.add(InetAddress.getByName("255.255.255.255"));
        } catch (Exception ignored) {
        }
        return list;
    }

    private int extractPort(String json) {
        try {
            int idx = json.indexOf("\"port\"");
            if (idx < 0) return 3000;
            int colon = json.indexOf(':', idx);
            int end = colon + 1;
            while (end < json.length() && Character.isDigit(json.charAt(end))) end++;
            return Integer.parseInt(json.substring(colon + 1, end).trim());
        } catch (Exception e) {
            return 3000;
        }
    }

    private void notifyFound(final String ip, final int port) {
        runOnUiThread(() -> webView.evaluateJavascript(
                "window.onServerFound && window.onServerFound('" + ip + "'," + port + ")", null));
    }

    private void notifyNotFound() {
        runOnUiThread(() -> webView.evaluateJavascript(
                "window.onServerNotFound && window.onServerNotFound()", null));
    }
}
