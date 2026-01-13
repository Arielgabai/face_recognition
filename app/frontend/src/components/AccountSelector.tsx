import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Box,
  Chip,
} from '@mui/material';

interface AccountInfo {
  user_id: number;
  username: string;
  user_type: string;
  event_id?: number;
  event_name?: string;
  event_code?: string;
  event_date?: string;
}

interface AccountSelectorProps {
  open: boolean;
  accounts: AccountInfo[];
  onSelectAccount: (account: AccountInfo) => void;
  onClose?: () => void;
}

const AccountSelector: React.FC<AccountSelectorProps> = ({
  open,
  accounts,
  onSelectAccount,
  onClose,
}) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h6" component="div">
          Sélectionnez votre événement
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Plusieurs comptes sont associés à cet identifiant. Veuillez choisir l'événement auquel vous souhaitez accéder.
        </Typography>
      </DialogTitle>
      <DialogContent>
        <List sx={{ pt: 0 }}>
          {accounts.map((account) => (
            <ListItem key={account.user_id} disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                onClick={() => onSelectAccount(account)}
                sx={{
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'action.hover',
                  },
                }}
              >
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle1">
                        {account.event_name || 'Événement'}
                      </Typography>
                      {account.user_type === 'photographer' && (
                        <Chip label="Photographe" size="small" color="primary" />
                      )}
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Nom d'utilisateur: {account.username}
                      </Typography>
                      {account.event_code && (
                        <Typography variant="body2" color="text.secondary">
                          Code: {account.event_code}
                        </Typography>
                      )}
                      {account.event_date && (
                        <Typography variant="body2" color="text.secondary">
                          Date: {new Date(account.event_date).toLocaleDateString('fr-FR')}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </DialogContent>
    </Dialog>
  );
};

export default AccountSelector;
