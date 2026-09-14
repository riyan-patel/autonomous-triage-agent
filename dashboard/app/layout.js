import "./globals.css";

export const metadata = {
  title: "Triage Agent Dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
