import 'package:flutter/material.dart';
import 'colors/colors.dart';
import 'fonts/fonts.dart';

class AppTheme {
  AppTheme._();

  static final ThemeData theme = ThemeData.dark().copyWith(
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      surface: AppColors.surface,
    ),
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
    ),
    cardColor: AppColors.card,
    dividerColor: AppColors.border,
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: AppColors.surface,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textSecondary,
      showUnselectedLabels: true,
    ),
    navigationBarTheme: const NavigationBarThemeData(
      height: 64,
      backgroundColor: AppColors.surface,
      indicatorColor: Color(0xFF162A48),
      labelTextStyle: WidgetStatePropertyAll(TextStyle(fontSize: 9)),
      iconTheme: WidgetStatePropertyAll(IconThemeData(size: 20)),
    ),
    textTheme: AppFonts.textTheme(AppColors.textPrimary),
  );
}
