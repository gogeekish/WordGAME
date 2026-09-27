package com.nextgen.enrollmentcount.login;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.Properties;

import javax.mail.Message;
import javax.mail.PasswordAuthentication;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;

public class MainActivity extends Activity {

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

        webView.loadUrl("file:///android_asset/index.html");
    }

    private class AndroidBridge {
        @JavascriptInterface
        public void sendEmail(final String fromEmail, final String appPassword, final String toEmail,
                               final String subject, final String body) {
            new Thread(() -> {
                try {
                    sendViaGmailSmtp(fromEmail, appPassword, toEmail, subject, body);
                    notifySent();
                } catch (Exception e) {
                    notifyFailed(e.getMessage() == null ? e.toString() : e.getMessage());
                }
            }).start();
        }
    }

    private void sendViaGmailSmtp(String fromEmail, String appPassword, String toEmail,
                                   String subject, String body) throws Exception {
        Properties props = new Properties();
        props.put("mail.smtp.auth", "true");
        props.put("mail.smtp.starttls.enable", "true");
        props.put("mail.smtp.host", "smtp.gmail.com");
        props.put("mail.smtp.port", "587");

        Session session = Session.getInstance(props, new javax.mail.Authenticator() {
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(fromEmail, appPassword);
            }
        });

        Message message = new MimeMessage(session);
        message.setFrom(new InternetAddress(fromEmail));
        message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(toEmail));
        message.setSubject(subject);
        message.setText(body);

        Transport.send(message);
    }

    private void notifySent() {
        runOnUiThread(() -> webView.evaluateJavascript(
                "window.onNextGenEmailSent && window.onNextGenEmailSent()", null));
    }

    private void notifyFailed(final String message) {
        final String escaped = message.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ");
        runOnUiThread(() -> webView.evaluateJavascript(
                "window.onNextGenEmailFailed && window.onNextGenEmailFailed('" + escaped + "')", null));
    }
}
