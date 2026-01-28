<?php

class ChangePasswordDriverDovecot 
{
	const
		NAME        = 'Dovecot',
		DESCRIPTION = 'Enables changing passwords in the Dovecot passwd file.';

	/**
	 * @var \MailSo\Log\Logger
	 */
	private $oLogger = null;

	function __construct(\RainLoop\Config\Plugin $oConfig, \MailSo\Log\Logger $oLogger)
	{
		$this->oLogger = $oLogger;
	}

	public static function isSupported() : bool
	{
		return true;
	}

	public static function configMapping() : array
	{
		return array();
	}

	public function ChangePassword(\RainLoop\Model\Account $oAccount, string $sPrevPassword, string $sNewPassword) : bool
	{
		$filePath = "{{ dovecot_passwd_file }}";
		$email = $oAccount->Email();
		
		try {
			// Read current users
			$users = $this->readUsers($filePath);
			$userFound = false;
			
			// Find and update the user's password
			foreach ($users as &$entry) {
				if ($entry['name'] === $email) {
					$userFound = true;
					// Verify old password matches (skip if extra_fields is "fail" - first password set)
					if ($entry['extra_fields'] !== 'fail') {
                        // check if pw starts with {BLF-CRYPT}, if not then it's a debug password stored in raw
                        $oldPw = $entry['passwd'];
                        $oldMatches = str_starts_with($oldPw, '{BLF-CRYPT}') ? 
                            password_verify($sPrevPassword, str_replace('{BLF-CRYPT}', '', $oldPw)) :
                            ($sPrevPassword === $oldPw);
                        if (!$oldMatches) {
							$this->oLogger->Write('Current password verification failed for ' . $email, \MailSo\Log\Enumerations\Type::ERROR);
							return false;
						}
					}
					
					// Update password with bcrypt hash
					$entry['passwd'] = '{BLF-CRYPT}' . password_hash($sNewPassword, PASSWORD_BCRYPT);
					$entry['extra_fields'] = '';
					break;
				}
			}
			
			if (!$userFound) {
				$this->oLogger->Write('User not found: ' . $email, \MailSo\Log\Enumerations\Type::ERROR);
				return false;
			}
			
			// Write updated users back to file
			$this->writeUsers($filePath, $users);
			$this->oLogger->Write('Password changed successfully for ' . $email, \MailSo\Log\Enumerations\Type::INFO);
			return true;
			
		} catch (\Exception $e) {
			$this->oLogger->Write('Error changing password: ' . $e->getMessage(), \MailSo\Log\Enumerations\Type::ERROR);
			return false;
		}
	}
	
	private function readUsers(string $filePath) : array
	{
		$result = [];
		$keys = ['name', 'passwd', 'uid', 'gid', 'gecos', 'dir', 'shell', 'extra_fields'];
		$handle = fopen($filePath, 'r');
		if (!$handle) {
			throw new \RuntimeException(
				"Failed to open $filePath for reading! " . print_r(error_get_last(), true)
			);
		}
		while (($values = fgetcsv($handle, 1000, ':')) !== false) {
			$values = array_pad($values, count($keys), '');
			$result[] = array_combine($keys, $values);
		}
		fclose($handle);
		return $result;
	}
	
	private function writeUsers(string $filePath, array $entries) : void
	{
		$handle = fopen($filePath, 'w');
		if (!$handle) {
			throw new \RuntimeException(
				"Failed to open $filePath for writing! " . print_r(error_get_last(), true)
			);
		}
		foreach ($entries as $entry) {
			fputcsv($handle, $entry, ':');
		}
		fclose($handle);
	}
}