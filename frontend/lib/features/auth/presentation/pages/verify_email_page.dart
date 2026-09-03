import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../shared/colors/colors.dart';
import '../../domain/auth_state.dart';
import '../providers/auth_provider.dart';
import '../widgets/auth_button.dart';
import '../widgets/auth_text_field.dart';

class VerifyEmailPage extends ConsumerStatefulWidget {
  final String email;

  const VerifyEmailPage({super.key, required this.email});

  @override
  ConsumerState<VerifyEmailPage> createState() => _VerifyEmailPageState();
}

class _VerifyEmailPageState extends ConsumerState<VerifyEmailPage> {
  final _formKey = GlobalKey<FormState>();
  final _otpController = TextEditingController();

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  void _handleVerify() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(authProvider.notifier).verifyEmail(
          email: widget.email,
          otp: _otpController.text.trim(),
        );
  }

  void _handleResend() {
    ref.read(authProvider.notifier).resendOtp(email: widget.email);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Verification code resent to ${widget.email}',
          style: GoogleFonts.roboto(color: Colors.white),
        ),
        backgroundColor: AppColors.success,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (prev, next) {
      if (next is AuthAuthenticated) {
        context.go('/');
      } else if (next is AuthError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.message),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    });

    final isLoading = authState is AuthLoading;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Icon
                    const Icon(
                      Icons.mark_email_read_outlined,
                      color: AppColors.primary,
                      size: 64,
                    ),
                    const SizedBox(height: 20),

                    // Title
                    Text(
                      'Verify Your Email',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'We sent a 6-digit code to',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.roboto(
                        color: AppColors.textSecondary,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.email,
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(
                        color: AppColors.primary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // OTP Input
                    AuthTextField(
                      controller: _otpController,
                      label: 'Verification Code',
                      hint: '000000',
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Enter the code';
                        if (v.trim().length != 6) return 'Code must be 6 digits';
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),

                    // Verify Button
                    AuthButton(
                      label: 'Verify Email',
                      isLoading: isLoading,
                      onPressed: isLoading ? null : _handleVerify,
                    ),
                    const SizedBox(height: 20),

                    // Resend
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          "Didn't receive the code? ",
                          style: GoogleFonts.roboto(
                            color: AppColors.textSecondary,
                            fontSize: 14,
                          ),
                        ),
                        AuthTextButton(
                          label: 'Resend',
                          onPressed: _handleResend,
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Back to Login
                    AuthTextButton(
                      label: '← Back to Sign In',
                      onPressed: () => context.go('/login'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
