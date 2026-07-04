package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
  primary = AccentOrange,
  onPrimary = Color.White,
  primaryContainer = AccentOrange,
  onPrimaryContainer = Color.White,
  secondary = AccentTeal,
  onSecondary = Color.Black,
  tertiary = AccentYellow,
  onTertiary = Color.Black,
  background = DarkBackground,
  onBackground = TextPrimary,
  surface = DarkSurface,
  onSurface = TextPrimary,
  surfaceVariant = CardSurface,
  onSurfaceVariant = TextSecondary,
  outline = TextSecondary
)

private val LightColorScheme = DarkColorScheme // Force dark space theme for NutriAI design consistency

@Composable
fun MyApplicationTheme(
  darkTheme: Boolean = true, // Force dark mode for NutriAI styling
  dynamicColor: Boolean = false, // Use our brand colors rather than wallpaper secondary palettes
  content: @Composable () -> Unit,
) {
  val colorScheme = if (darkTheme) DarkColorScheme else DarkColorScheme

  MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}
